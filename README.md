# airpurifier2mqtt

Bridge between Xiaomi Airpurifier 3H and MQTT.

The script uses [python-miio library](https://github.com/rytilahti/python-miio) to communicate with air purifier. In order to get the communication working you need to get your device token. Refer to [python-miio Getting started](https://python-miio.readthedocs.io/en/latest/discovery.html) section to find out how to obtain it.

## Features

### Getting air purifier state

The scripts polls multiple air purifiers state and publishes it to MQTT broker as a JSON. Example payload published for air purifier defined in configuration file as `my-purifier` to MQTT topic `airpurifier/my-airpurifier/state`:

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

Air purifier can be controlled by publishing JSON formatted commands to MQTT topic.
For example if you want to power on your device defined in configuration file as `my-airpurifier` then you need publish following JSON message to topic `airpurifier/my-airpurifier/set`

```json
{"power": "on"}
```

You can publish multiple command at once, for example:

```json
{"power": "off", "mode": "Favorite", "favirote_level": 10}
```

## Installation

### You will need

* *airpurifier2mqtt.py* - script which does the job
* *airpurifier2mqtt.yaml* - configuration file
* Python (at least 3.8)
* Running MQTT broker

### Installation steps

1. Create directory (for example */opt/airpurifier2mqtt*) and put inside *airpurifier2mqtt.py*
    ```
    cd /opt
    mkdir airpurifier2mqtt
    cd airpurifier2mqtt
    curl -o airpurifier2mqtt.py 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/master/airpurifier2mqtt.py'
    ```

2. Create python virtual environment 
    ```
    python3 -m venv env
    ```

3. Install dependencies
    ```
    curl -o requirements.txt 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/master/requirements.txt'
    env/bin/python -m pip install --upgrade pip -r requirements.txt
    ```

3. Install configuration file (for example in */etc*)
    ```
    sudo curl -o /etc/airpurifier2mqtt.yaml 'https://raw.githubusercontent.com/mikozak/airpurifier2mqtt/master/airpurifier2mqtt.yaml'
    ```

4. Edit configuration file installed in previous step.

5. Run it
    ```
    env/bin/python airpurifier2mqtt.py --config /etc/airpurifier2mqtt.yaml
    ```

### Installation as a service

1. Create system user which will be used to run service process (for the purpose of this instruction user named *airpurifier2mqtt* will be used)
    ```
    sudo useradd -r airpurifier2mqtt
    ```

2. Install service
    ```
    sudo curl -o /etc/systemd/system/airpurifier2mqtt.service 'https://raw.githubusercontent.com/mikozak/deconz2mqtt/master/airpurifier2mqtt.service'
    ```

3. Verify and edit if needed in `/etc/systemd/system/airpurifier2mqtt.service`:
    * `WorkingDirectory` and `ExecStart` paths are valid (and absolute!)
    * `User` is correct (equals username created in step 1)

4. Start service
    ```
    sudo systemctl start airpurifier2mqtt
    ```

    If you want to start the service automatically after system restart you need to enable it
    ```
    sudo systemctl enable airpurifier2mqtt
    ```
