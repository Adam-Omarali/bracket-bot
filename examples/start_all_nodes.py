#!/usr/bin/env python3
import libtmux
import sys
import os

def create_dev_environment():
    # Create a new server instance
    server = libtmux.Server()

    # Define session name
    SESSION_NAME = "dev-environment"

    # Kill existing session if it exists
    try:
        existing_session = server.get_session(SESSION_NAME)
        if existing_session:
            existing_session.kill()
    except:
        pass

    try:
        # Start a new session
        session = server.new_session(
            session_name=SESSION_NAME,
            window_name="main",
            detach=True
        )

        # Get the first window
        main_window = session.windows[0]
        main_pane = main_window.attached_pane

        # Split window vertically into two panes
        right_pane = main_pane.split_window(vertical=True)
        
        # Split both panes horizontally to create 2x2 grid
        bottom_left_pane = main_pane.split_window()
        bottom_right_pane = right_pane.split_window()

        # Ensure even layout
        main_window.select_layout('tiled')

        # Send commands to each pane in 2x2 grid
        main_pane.send_keys('cd ~/quickstart/examples && python3 lqr_balance_pubsub.py')
        right_pane.send_keys('cd ~/quickstart/examples && python3 node_autodeploy_legs.py')
        bottom_left_pane.send_keys('cd ~/quickstart/examples && python3 game_interface.py')
        bottom_right_pane.send_keys('cd ~/quickstart/examples && python3 -m http.server 8080')

        print(f"Tmux session '{SESSION_NAME}' created successfully!")
        
        # Attach to session if not already in tmux
        if not os.environ.get('TMUX'):
            os.system(f"tmux attach -t {SESSION_NAME}")
        else:
            print(f"To attach to this session later, use: tmux attach -t {SESSION_NAME}")

    except Exception as e:
        print(f"Error creating tmux session: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_dev_environment()
