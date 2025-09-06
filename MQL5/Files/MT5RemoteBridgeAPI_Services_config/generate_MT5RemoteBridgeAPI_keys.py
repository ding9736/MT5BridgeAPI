# generate_MT5RemoteBridgeAPI_Services_config_keys.py   Generates and prints a new MT5RemoteBridgeAPI_Services_config CURVE key pair

import zmq


def generate_curve_keypair():
    """
    Generates and prints a new MMT5RemoteBridgeAPI_Services_config CURVE key pair.
    """
    try:
        public_key, secret_key = zmq.curve_keypair()

        print("-" * 60)
        print(
            "Your new MT5RemoteBridgeAPI CURVE key pair has been generated successfully!"
        )
        print(
            "Please copy the following lines into your MT5RemoteBridgeAPI_Config.json file."
        )
        print("-" * 60)
        print(f'"ServerPublicKey": "{public_key.decode("utf-8")}",')
        print(f'"ServerSecretKey": "{secret_key.decode("utf-8")}",')
        print("-" * 60)

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure 'pyzmq' is installed ('pip install pyzmq').")


if __name__ == "__main__":
    generate_curve_keypair()
