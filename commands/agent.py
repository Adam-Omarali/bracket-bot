import paho.mqtt.client as mqtt
from commands.planning import execute_task
# MQTT settings
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC_COMMAND = "robot/command"

def setup_mqtt():
    def on_connect(client, userdata, flags, rc):
        print("Connected to MQTT broker with result code " + str(rc))
        # Subscribe to command topic
        client.subscribe(MQTT_TOPIC_COMMAND)

    def on_message(client, userdata, msg):
        if msg.topic == MQTT_TOPIC_COMMAND:
            command = msg.payload.decode()
            print(f"Received command: {command}")
            execute_task(command)
            # Here you can add logic to process the command
            # For example, parse it and call appropriate functions

    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to broker
    try:
        client.connect(MQTT_BROKER_ADDRESS, 1883, 60)
        client.loop_start()
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")

    return client

# Initialize MQTT when module is loaded
mqtt_client = setup_mqtt()

if __name__ == '__main__':
    try:
        # Keep the script running
        while True:
            pass
    except KeyboardInterrupt:
        print("Shutting down...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()