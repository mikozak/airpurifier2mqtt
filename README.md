# airpurifier2mqtt

Bridge between Xiaomi Air Purifier 3H and MQTT written in [python asyncio](https://docs.python.org/3/library/asyncio.html).

![Diagram](https://github.com/mikozak/airpurifier2mqtt/blob/main/doc/assets/diagram.png "Diagram")

The script uses [python-miio](https://github.com/rytilahti/python-miio) to communicate with air purifier. In order to
get the communication working you need to get your device token. Refer to [Getting
started](https://python-miio.readthedocs.io/en/latest/discovery.html) section of *python-miio* to find out how to obtain
it.

## Features

### Getting air purifier state

The script polls multiple air purifiers states and publishes them to MQTT broker as a JSON. Example JSON payload published for
air purifier defined in configuration file as `my-airpurifier` to MQTT topic `airpurifier/my-airpurifier/state`:

```json
{
  "temperature": 20.9,
  "power": "on",
  "aqi": 8,
  "average_aqi": 23,
  "humidity": 50,
  "fan_level": 2,
  "filter_hours_used": 43,
  "filter_life_remaining": 98,
  "favorite_level": 5,
  "child_lock": false,
  "led": true,
  "motor_speed": 1262,
  "purify_volume": 5182,
  "use_time": 156000,
  "buzzer": false,
  "filter_rfid_product_id": "0:0:31:31",
  "filter_rfid_tag": "80:6c:50:1a:33:49:4",
  "mode": "Favorite",
  "led_brightness": "Off",
  "filter_type": "Regular"
}
```

### Controlling air purifier

Air purifier can be controlled by publishing JSON formatted commands to MQTT topic. For example, if you want to power on
your device defined in configuration file as `my-airpurifier`, then you need to publish following JSON message to topic
`airpurifier/my-airpurifier/set`:

```json
{"power": "on"}
```

You can publish multiple commands at once, for example:

```json
{"power": "off", "mode": "Favorite", "favirote_level": 10}
```

#### Supported commands

* *power*
* *mode*
* *favorite_level*

## Installation

### You will need

* *airpurifier2mqtt.py* - script which does the job
* *airpurifier2mqtt.yaml* - configuration file
* Python (at least 3.8)
* Running MQTT broker

### Installation steps

1. Create directory (for example */opt/airpurifier2mqtt*) and put inside *airpurifier2mqtt.py*

    ```bash
    cd /opt
    mkdir airpurifier2mqtt
    cd airpurifier2mqtt
    curl -o airpurifier2mqtt.py 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/main/airpurifier2mqtt.py'
    ```

2. Create python virtual environment 

    ```bash
    python3 -m venv env
    ```

3. Install dependencies

    ```bash
    curl -o requirements.txt 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/main/requirements.txt'
    env/bin/python -m pip install --upgrade pip -r requirements.txt
    ```

4. Install configuration file (for example in */etc*)

    ```bash
    sudo curl -o /etc/airpurifier2mqtt.yaml 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/main/airpurifier2mqtt.yaml'
    ```

5. Edit configuration file installed in previous step.

6. Run it

    ```bash
    env/bin/python airpurifier2mqtt.py --config /etc/airpurifier2mqtt.yaml
    ```

### Installation as a service

1. Create system user which will be used to run service process (for the purpose of this instruction user named
   *airpurifier2mqtt* will be used)

    ```bash
    sudo useradd -r airpurifier2mqtt
    ```

2. Install service

    ```bash
    sudo curl -o /etc/systemd/system/airpurifier2mqtt.service 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/main/airpurifier2mqtt.service'
    ```

3. Verify and edit if needed in `/etc/systemd/system/airpurifier2mqtt.service`:
    * `WorkingDirectory` and `ExecStart` paths are valid (and absolute!)
    * `User` is correct (equals username created in step 1)

4. Start service

    ```bash
    sudo systemctl start airpurifier2mqtt
    ```

    If you want to start the service automatically after system restart you need to enable it

    ```bash
    sudo systemctl enable airpurifier2mqtt
    ```
