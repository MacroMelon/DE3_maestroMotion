import socket
import re
from scipy.spatial.transform import Rotation as R
from pythonosc.udp_client import SimpleUDPClient
import re
import numpy as np
# UDP Setup
UDP_IP = "127.0.0.1"
UDP_RECEIVE_PORT = 7500
UDP_OUT_PORT = 7600  # Sending back to MaxMSP
client = SimpleUDPClient(UDP_IP, UDP_OUT_PORT)  # OSC Client

# Define the primary reference frame (default position and rotation)
primary_position = np.array([0, 0, 0])
primary_rotation = np.array([0, 0, 0])  # No rotation

# Define the camera reference frame (relative to primary)
camera_position = np.array([0, 0, 2])
camera_rotation = np.array([0, 0, 0])  # Will be updated dynamically

# Transformation matrix (identity by default)
transformation_matrix = np.eye(4)  

# Create a UDP socket
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((UDP_IP, UDP_RECEIVE_PORT))
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Listening on {UDP_IP}:{UDP_RECEIVE_PORT}...")


def compute_transformation_matrix(rotation, position):
    """
    Compute 4x4 transformation matrix from Euler angles and position.
    - Rotation: roll, pitch, yaw in degrees
    - Position: (x, y, z)
    """
    rot_matrix = R.from_euler('xyz', rotation, degrees=True).as_matrix()  # Convert rotation to matrix
    transform_matrix = np.eye(4)  # Initialize identity matrix (4x4)
    transform_matrix[:3, :3] = rot_matrix  # Set rotation part
    transform_matrix[:3, 3] = position  # Set translation part
    return transform_matrix

while True:
    data, addr = recv_sock.recvfrom(1024)
    message = data.decode('utf-8', errors="ignore").strip()  # Remove decoding errors

    # Debug: Print raw received message
    print(f"Raw Message: {repr(message)}")

    # Split the message
    parts = message.split()
    print(f"Split Parts: {parts}")

    # Ensure valid format (prefix + 3 values)
    if len(parts) >= 4:
        # Clean up the prefix (remove null bytes at the end)
        parts[0] = parts[0].replace("\x00", "")
        


        # Remove unwanted prefix in the first float
        parts[1] = re.sub(r"^s\x00+", "", parts[1])

        # Remove unwanted null bytes in the last float
        parts[3] = re.sub(r"[\x00,]+$", "", parts[3])
        
        # Ignore any unexpected additional parts (remove index 4+)
        parts = parts[:4]


        try:
            # Extract and convert float values
            values = list(map(float, parts[1:4]))  # Expecting exactly 3 floats
            prefix = parts[0]
            
            if prefix == "/camera_rotation":
                # Update camera rotation
                camera_rotation = np.array(values)

                # Compute transformation matrix for camera (secondary frame to primary frame)
                transformation_matrix = compute_transformation_matrix(camera_rotation, camera_position)

                print(f"Updated Camera Rotation: {camera_rotation}")
                print(f"Transformation Matrix:\n{transformation_matrix}")



            elif prefix == "/object_location":
                # Receive object location relative to the secondary frame (camera)
                print("Received `/object_location`!")
                object_position = np.array(values + [1])  # Convert to homogeneous coordinates (x, y, z, 1)
                print(f"Object Position (Secondary Frame, Homogeneous): {object_position}")
          
                print(f"Applying Transformation Matrix:\n{transformation_matrix}")

                # Transform object position to primary reference frame
                transformed_position = transformation_matrix @ object_position
                transformed_position = transformed_position[:3]  # Extract (x, y, z)

                print(f"Object Location (Secondary): {object_position[:3]}")
                print(f"Transformed Location (Primary): {transformed_position}")

                # Send transformed object position back to MaxMSP
                #send_udp(f"/object_location {transformed_position[0]:.2f} {transformed_position[1]:.2f} {transformed_position[2]:.2f}")
                
                client.send_message("/object_new_location", [transformed_position[0], transformed_position[1], transformed_position[2]])


            print(f"Prefix: {prefix}")
            print(f"Extracted Values: {values}")

        except ValueError:
            print(f"Invalid numerical conversion: {message}")

    else:
        print(f"Invalid data received: {message}")