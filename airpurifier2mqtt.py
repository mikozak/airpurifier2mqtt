from timeit import default_timer as timer
import functools
import argparse
import asyncio
import io
import json
import logging
import yaml

from dotmap import DotMap
from hbmqtt.client import ConnectException
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt.constants import QOS_0
from miio.airpurifier_miot import AirPurifierMiotStatus
import miio

class ConfigurationException(Exception):
    """Configuration error"""
    pass

class DeviceStatus:
    """Air purifier status"""
    def __init__(self, name: str, status: AirPurifierMiotStatus):
        self._name = name
        self._status = status

    @property
    def name(self):
        return self._name

    @property
    def status(self):
        return self._status

class AirPurifierMiotEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, AirPurifierMiotStatus):
            return {
                'temperature': o.temperature,
                'power': o.power,
                'aqi': o.aqi,
                'average_aqi': o.average_aqi,
                'humidity': o.humidity,
                'fan_level': o.fan_level,
                'filter_hours_used': o.filter_hours_used,
                'filter_life_remaining': o.filter_life_remaining,
                'favorite_level': o.favorite_level,
                'child_lock': o.child_lock,
                'led': o.led,
                'motor_speed': o.motor_speed,
                'purify_volume': o.purify_volume,
                'use_time': o.use_time,
                'buzzer': o.buzzer,
                'filter_rfid_product_id': o.filter_rfid_product_id,
                'filter_rfid_tag': o.filter_rfid_tag,
                'mode': o.mode.name,
                'led_brightness': o.led_brightness.name,
                'filter_type': o.filter_type.name
            }
        return json.JSONEncoder.default(self, o)

def _device_status(airpurifier: miio.AirPurifierMiot, log: logging.Logger):
    """
    Gets device status asynchronously.

    Returns device status or None in case status cannot be fetched or some
    errors occured during fetching.
    """
    def status(airpurifier: miio.AirPurifierMiot, log: logging.Logger):
        log.debug('Polling state...')
        try:
            polling_start = timer()
            status = airpurifier.status()
            log.debug('Polling state succeeded and took %.3fs', timer() - polling_start)
            return status
        except Exception as error:
            log.warning('Polling state failed and took %.3fs. Reason is %s: %s',
                timer() - polling_start,
                '.'.join([error.__class__.__module__, error.__class__.__qualname__]),
                error)
            raise
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, status, airpurifier, log)

def _device_command(log: logging.Logger, airpurifier: miio.AirPurifierMiot, name: str, *args):
    def command(airpurifier: miio.AirPurifierMiot, name: str, log: logging.Logger, *args):
        try:
            command_start = timer()
            getattr(airpurifier, name)(*args)
            log.debug('Command "%s" succeeded and took %.3fs', 
                name,
                timer() - command_start)
            return True
        except Exception as error:
            log.warning('Command "%s" failed and took %.3fs. Reason is %s: %s',
                name,
                timer() - command_start,
                '.'.join([error.__class__.__module__, error.__class__.__qualname__]),
                error)
            raise
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, command, airpurifier, name, log, *args)

def _retry(coro, retries: int = 3, interval: float = 1, fail_result = None, log = None):
    """
    Retries coroutine
    """
    async def _retry_wrapper(*args, **kwargs):
        nonlocal retries
        retries = 0 if retries < 0 else retries
        while retries >= 0:
            try:
                return await coro(*args, **kwargs)
            except Exception:
                if retries <= 0:
                    return fail_result
                if log:
                    log.info('Retry in %.3fsec. Retries left: %d',
                        interval,
                        retries)
                retries -= 1
                await asyncio.sleep(interval)
    return _retry_wrapper

async def _create_mqtt_client(mqtt_config: DotMap, log: logging.Logger = None):
    """
    Create new MQTT client and connect to MQTT broker
    """
    mqtt_client = MQTTClient(config=mqtt_config.client)
    log = log if not log is None else logging.getLogger('airpurifier2mqtt.mqtt')
    try:
        log.info('Connecting to MQTT')
        await mqtt_client.connect(
            uri=mqtt_config.client.uri,
            cleansession=mqtt_config.client.cleansession)
        return mqtt_client
    except ConnectException as connection_exception:
        log.error('Can\'t connect to MQTT: %s', connection_exception)
        raise
    finally:
        log.info('Connected to MQTT')

async def mqtt_publisher(mqtt: DotMap, device_status_queue: asyncio.Queue):
    log = logging.getLogger('airpurifier2mqtt.mqtt.publisher')
    mqtt_client = await _create_mqtt_client(mqtt, log=log)
    while True:
        device_status = await device_status_queue.get()
        mqtt_topic = '{}/{}/state'.format(mqtt.topic_prefix, device_status.name)
        mqtt_payload = json.dumps(device_status.status, cls=AirPurifierMiotEncoder).encode('utf-8')
        log.debug('Publishing: topic=%s payload=%s', mqtt_topic, mqtt_payload)
        await mqtt_client.publish(mqtt_topic, mqtt_payload)

async def mqtt_subscriber(mqtt: DotMap, device_command_queues: dict):
    log = logging.getLogger('airpurifier2mqtt.mqtt.subscriber')
    mqtt_client = await _create_mqtt_client(mqtt, log=log)
    await mqtt_client.subscribe([('{}/+/set'.format(mqtt.topic_prefix), QOS_0)])
    while True:
        message = await mqtt_client.deliver_message()
        log.debug('Got message topic=%s payload=%s', message.topic, message.data.decode('utf-8'))
        device_name = message.topic[len(mqtt.topic_prefix):].lstrip('/').partition('/')[0]
        payload = message.data.decode('utf-8')
        try:
            payload_json = json.loads(payload)
            device_command_queues[device_name].put_nowait(payload_json)
            log.debug('Scheduled command for device "%s"', device_name)
        except asyncio.QueueFull:
            log.warning('Scheduling command for device "%s" failed. Device command queue is full!',
                device_name)
        except json.decoder.JSONDecodeError as json_error:
            log.error('Error parsing JSON payload "%s". %s: %s',
                payload,
                '.'.join([json_error.__class__.__module__, json_error.__class__.__qualname__]),
                json_error)

def _create_device(device_config: DotMap):
    return miio.AirPurifierMiot(device_config.ip, device_config.token)

async def device_command(device_config: DotMap, device_command_queue: asyncio.Queue, force_poll_event: asyncio.Event):
    """
    Sends commands enqueued in `device_command_queue` to device
    """
    log = logging.getLogger('airpurifier2mqtt.command.{}'.format(device_config.name))
    while True:
        command_json = await device_command_queue.get()
        device = _create_device(device_config)
        command = functools.partial(_retry(_device_command, fail_result=False, log=log), log, device)
        log.debug('Processing command for device "%s": %s', device_config.name, command_json)
        for property_name, property_value in command_json.items():
            if property_name == 'power' and property_value in ('on', 'off'):
                await command(property_value)
            elif property_name == 'mode' and property_value in ('Auto', 'Silent', 'Favorite', 'Fan'):
                await command('set_mode', miio.airpurifier_miot.OperationMode[property_value])
            elif property_name == 'favorite_level' and isinstance(property_value, int) and property_value >= 0 and property_value <= 14:
                await command('set_favorite_level', property_value)
            else:
                log.error('Unknown command "%s" or invalid command value or value type "%s"',
                    property_name,
                    property_value)
        force_poll_event.set()

async def device_polling(device_config: DotMap, device_status_queue: asyncio.Queue, force_poll_event: asyncio.Event):
    log = logging.getLogger('airpurifier2mqtt.state.{}'.format(device_config.name))
    device = _create_device(device_config)
    while True:
        if force_poll_event.is_set():
            log.debug('Polling device state has been forced')
        retryable_device_status = _retry(
            _device_status, 
            retries = device_config.polling.get('retries', 0), 
            interval = device_config.polling.get('retry_interval', 10),
            log = log)
        status = await retryable_device_status(device, log)
        if status:
            device_status = DeviceStatus(device_config.name, status)
            if device_status_queue.full():
                log.warning('Status queue is full. Polling will be suspended')
            await device_status_queue.put(device_status)
            log.debug('Device status enqueued')
        polling_interval = device_config.polling.get('interval', 120)
        log.debug('Next polling in %ds', polling_interval)
        force_poll_event.clear()
        await asyncio.wait([force_poll_event.wait()], timeout=polling_interval)

async def start(config: DotMap):
    """
    This is coroutine.

    Starts polling device state and publishing it to mqtt.
    Subscribes mqtt for commands and sends them to device.
    """
    log = logging.getLogger('airpurifier2mqtt')
    devices_status_queue = asyncio.Queue(3 * len(config.devices))
    tasks = []
    device_command_queues = {}
    for device in config.devices:
        # create polling task
        force_poll_event = asyncio.Event()
        task_name = 'device-polling-{}'.format(device.name)
        task = asyncio.create_task(device_polling(device, devices_status_queue, force_poll_event), name=task_name)
        tasks.append(task)
        # create command task
        task_name = 'device-command-{}'.format(device.name)
        command_queue = asyncio.Queue(64)
        device_command_queues[device.name] = command_queue
        task = asyncio.create_task(device_command(device, command_queue, force_poll_event), name=task_name)
        tasks.append(task)
    tasks.append(asyncio.create_task(mqtt_publisher(config.mqtt, devices_status_queue), name='mqtt-publisher'))
    tasks.append(asyncio.create_task(mqtt_subscriber(config.mqtt, device_command_queues), name='mqtt-subscriber'))
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for task in done:
        try:
            task.result()
        except Exception as error:
            log.error('Finishing because of error: %s', error)
    for task in pending:
        task.cancel()

def _to_config(dictionary: DotMap):
    if not dictionary.devices:
        raise ConfigurationException('No devices configured')
    device_names = []
    for device in dictionary.devices:
        if not device.name:
            raise ConfigurationException('One of a device is missing name')
        if device.name in device_names:
            raise ConfigurationException('Device "{name}" is defined more than once'\
                .format(**device))
        device_names.append(device.name)
        if not device.ip:
            raise ConfigurationException('Device "{name}" is missing ip'\
                .format(**device))
        if not device.token:
            raise ConfigurationException('Device "{name}" is missing token'\
                .format(**device))
    return dictionary

def _main():
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()

    # read config file
    with io.open(args.config, 'r') as stream:
        config = _to_config(DotMap(yaml.safe_load(stream)))

    # configure logging
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s%(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    # read loggers configuration from config
    for logger_name, logger_level in config.logging.items():
        logging.getLogger(None if logger_name == 'root' else logger_name).setLevel(logger_level)

    asyncio.run(start(config))

if __name__ == "__main__":
    _main()
