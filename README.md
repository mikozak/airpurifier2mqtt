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
  "power": "On",
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

Air purifier can be controlled by publishing JSON formatted commands to MQTT. For example, if you want to power on
your device defined in configuration file as `my-airpurifier`, then you need to publish following JSON message to topic
`airpurifier/my-airpurifier/set`:

```json
{"power": "On"}
```

You can publish multiple commands at once, for example:

```json
{"power": "Off", "mode": "Favorite", "favirote_level": 10}
```

There is also an alternative way. You can include command name in MQTT topic like this 
`airpurifier/my-airpurifier/set/power` with payload `On` to power on air purifier.

#### Supported commands

* *power*. Possible values: `"On"`, `"Off"`
* *mode*. Possible values: 
  * `"Auto"` - corresponds to "Auto" mode in *Xiaomi Home* app 
  * `"Silent"` - corresponds to "Night" mode in *Xiaomi Home* app
  * `"Favorite"` - corresponds to "Manual" mode in *Xiaomi Home* app
  * `"Fan"` - corresponds to "Level" mode in *Xiaomi Home* app
* *favorite_level*. Fan speed in "Favorite" mode. Possible value is integer from `0` to `14`

## Home Assistant integration

### Lovelace card

<img src="https://github.com/mikozak/airpurifier2mqtt/blob/main/doc/assets/lovelace%20card.png" width="490"/>

This example uses [multiple-entity-row](https://github.com/benct/lovelace-multiple-entity-row).

```yaml
type: entities
title: Air purifier
show_header_toggle: false
entities:
  - entity: fan.air_purifier_xiaomi_3h_1
    type: 'custom:multiple-entity-row'
    toggle: true
    state_color: true
    name: Fan
    secondary_info:
      attribute: favorite_level
      name: 'Speed (0-14):'
  - entity: sensor.air_purifier_xiaomi_3h_1_aqi
    type: 'custom:multiple-entity-row'
    name: PM 2.5
    state_header: current
    secondary_info: last-updated
    unit: μg/m³
    icon: 'mdi:dots-hexagon'
    entities:
      - entity: fan.air_purifier_xiaomi_3h_1
        attribute: average_aqi
        name: average
        unit: μg/m³
```

### Configuration

```yaml
fan:
  - platform: mqtt
    name: air_purifier_xiaomi_3h_1
    unique_id: air_purifier_xiaomi_3h_1
    command_topic: 'airpurifier/airpurifier-3h-1/set/power'
    json_attributes_topic: 'airpurifier/airpurifier-3h-1/state'
    state_topic: 'airpurifier/airpurifier-3h-1/state'
    state_value_template: '{{ value_json.power }}'
    payload_on: 'On'
    payload_off: 'Off'
    optimistic: true

sensor:
  - platform: template
    sensors:
      air_purifier_xiaomi_3h_1_aqi:
        value_template: "{{ state_attr('fan.air_purifier_xiaomi_3h_1', 'aqi') }}"

automation:
  - id: 'air_purifier_xiaomi_3h_1_off'
    alias: 'Air purifier: Off'
    trigger:
      - platform: numeric_state
        entity_id: sensor.air_purifier_xiaomi_3h_1_aqi
        below: 15
        for:
          minutes: 3
    condition: "{{ states('fan.air_purifier_xiaomi_3h_1') == 'on' }}"
    action:
      - service: fan.turn_off
        entity_id: fan.air_purifier_xiaomi_3h_1
  - id: 'air_purifier_xiaomi_3h_1_on'
    alias: 'Air purifier: On'
    trigger:
      - platform: numeric_state
        entity_id: sensor.air_purifier_xiaomi_3h_1_aqi
        above: 18
        for:
          minutes: 3
    condition: "{{ states('fan.air_purifier_xiaomi_3h_1') == 'off' }}"
    action:
      - service: mqtt.publish
        data:
          topic: airpurifier/airpurifier-3h-1/set
          payload: '{"mode": "Favorite", "favorite_level": 1}'
  - id: 'air_purifier_xiaomi_3h_1_speed'
    alias: 'Air purifier: Select speed'
    trigger:
      - platform: time_pattern
        minutes: '/5'
    condition: "{{ states('fan.air_purifier_xiaomi_3h_1') == 'on' }}"
    action:
      - service: mqtt.publish
        data:
          topic: airpurifier/airpurifier-3h-1/set/favorite_level
          payload_template: >
              {% if states('sensor.air_purifier_xiaomi_3h_1_aqi') | int > 30 %}
                10
              {% elif states('sensor.air_purifier_xiaomi_3h_1_aqi') | int > 25 %}
                7
              {% elif states('sensor.air_purifier_xiaomi_3h_1_aqi') | int > 20 %}
                6
              {% elif states('sensor.air_purifier_xiaomi_3h_1_aqi') | int > 15 %}
                3
              {% elif states('sensor.air_purifier_xiaomi_3h_1_aqi') | int > 10 %}
                2
              {% else %}
                0
              {% endif %}
```

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

## Installation on Docker

### You will need
* a Running docker environment, tested on Raspberry OS
* git installed on the host docker is running
* a running mqtt broker reachable from docker

### Build docker image
1. Clone the git repository to a directory of your choice
2. Build the image
```bash
cd airpurifier2mqtt
docker build -t airpurifier2mqtt .
```
3. Create a directory to hold your configuration data
For example:
```bash
mkdir /docker/volumes/airpurifier2mqtt/data
```
4. Create and modify the configuration yaml (Only when running the container for the first time) 

In the directory created above, install the provided example configuration
```bash
cp ./airpurifier2mqtt.yaml /docker/volumes/airpurifier2mqtt/data/airpurifier2mqtt.yaml
```
Update at the IP address and token of the Air Purifier as well as the URL of the MQTT Server

5. Start the container

Replace <path_to_config_dir> by the absolute path of the directory in 3
```bash
docker run --network host --name airpurifier2mqtt -v <path_to_config_dir>:/data airpurifier2mqtt
```
So it looks like this if you follow my example above
```bash
docker run --network host --name airpurifier2mqtt -v /docker/volumes/airpurifier2mqtt/data:/data airpurifier2mqtt
```

