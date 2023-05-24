#!/usr/bin/env python

# Import libraries
import socketio
import eventlet
from flask import Flask
from itertools import chain
import autodrive
import numpy as np
import time
import argparse

################################################################################

# Initialize vehicle(s)
v_1 = autodrive.Vehicle()
v_1.id = 'V1'

# Initialize the server
sio = socketio.Server()

# Flask (web) app
app = Flask(__name__) # '__main__'

# Registering "connect" event handler for the server
@sio.on('connect')
def connect(sid, environ):
    print('Connected!')

# Registering "Bridge" event handler for the server
@sio.on('Bridge')
def bridge(sid, data):
    if data:
        ################################################################################
        # Straight maneuver (constant throttle and zero steering)
        if maneuver == 'straight':
            t_straight = 90e9 # Time for straight maneuver
            # Straight
            if (time.time_ns() - t_start) <= t_straight:
                throttle_cmd = throttle + np.random.normal(0,throttle_noise) # Constant throttle (with noise)
                steering_cmd = 0 + np.random.normal(0,steering_noise) # Zero steering (with noise)
                print("Time : {:.4f} sec | Throttle : {:.2f} % | Steering : {:.4f} rad".format((time.time_ns()-t_start)/1e9, throttle_cmd*100, min(steering_cmd, 0.5236))) # Verbose
            # Stop
            else:
                throttle_cmd = 0 # Zero throttle
                steering_cmd = 0 # Zero steering
                print('Straight maneuver completed!') # Verbose
        ################################################################################
        # Skidpad maneuver (constant throttle and constant steering)
        if maneuver == 'skidpad':
            t_skidpad = 90e9 # Time for skidpad maneuver
            # Skidpad
            if (time.time_ns() - t_start) <= t_skidpad:
                throttle_cmd = throttle + np.random.normal(0,throttle_noise) # Constant throttle (with noise)
                steering_cmd = steering + np.random.normal(0,steering_noise) # Constant steering (with noise)
                print("Time : {:.4f} sec | Throttle : {:.2f} % | Steering : {:.4f} rad".format((time.time_ns()-t_start)/1e9, throttle_cmd*100, min(steering_cmd, 0.5236))) # Verbose
            # Stop
            else:
                throttle_cmd = 0 # Zero throttle
                steering_cmd = 0 # Zero steering
                print('Skidpad maneuver completed!') # Verbose
        ################################################################################
        # Fishhook maneuver (constant throttle and ramp steering)
        elif maneuver == 'fishhook':
            t_fishhook = 90e9 # Time for fishhook maneuver
            k_fishhook = 6e-12 # Controls steering rate (e.g. 1e-11 steers slower than 1e-10)
            # Fishhook
            if (time.time_ns() - t_start) <= t_fishhook:
                throttle_cmd = throttle + np.random.normal(0,throttle_noise) # Constant throttle (with noise)
                steering_cmd = k_fishhook*(time.time_ns() - t_start) + np.random.normal(0,steering_noise) # Time-dependent ramp steering (with noise)
                print("Time : {:.4f} sec | Throttle : {:.2f} % | Steering : {:.4f} rad".format((time.time_ns()-t_start)/1e9, throttle_cmd*100, min(steering_cmd, 0.5236))) # Verbose
            # Stop
            else:
                throttle_cmd = 0 # Zero throttle
                steering_cmd = 0 # Zero steering
                print('Fishhook maneuver completed!') # Verbose
        ################################################################################
        # Slalom maneuver (constant throttle and sinusoidal steering)
        elif maneuver == 'slalom':
            t_straight = 3e9 # Time for driving straight
            #t_straight = (0.5/throttle)*1e9 # Throttle-dependent time for driving straight
            t_slalom = 90e9 # Time for slalom maneuver
            #t_slalom = (5/throttle)*1e9 # Throttle-dependent time for slalom maneuver
            k_slalom = 9e-10 # Controls steering rate (e.g. 9e-10 steers slower than 1e-9)
            # Straight
            if (time.time_ns() - t_start) <= t_straight:
                throttle_cmd = throttle + np.random.normal(0,throttle_noise) # Constant throttle (with noise)
                steering_cmd = 0 + np.random.normal(0,steering_noise) # Zero steering (with noise)
                print("Time : {:.4f} sec | Throttle : {:.2f} % | Steering : {:.4f} rad".format((time.time_ns()-t_start)/1e9, throttle_cmd*100, min(steering_cmd, 0.5236))) # Verbose
            # Slalom
            elif (time.time_ns() - t_start) > t_straight and (time.time_ns() - t_start) <= (t_straight + t_slalom):
                throttle_cmd = throttle + np.random.normal(0,throttle_noise) # Constant throttle (with noise)
                steering_cmd = steering*np.cos(k_slalom*(time.time_ns() - (t_start + t_straight))) + np.random.normal(0,steering_noise) # Time-dependent sinusoidal steering (with noise)
                print("Time : {:.4f} sec | Throttle : {:.2f} % | Steering : {:.4f} rad".format((time.time_ns()-t_start)/1e9, throttle_cmd*100, min(steering_cmd, 0.5236))) # Verbose
            # Stop
            else:
                throttle_cmd = 0 # Zero throttle
                steering_cmd = 0 # Zero steering
                print('Slalom maneuver completed!') # Verbose
        ################################################################################
        # Limit actuation
        if steering_cmd >= 0.5236:
            steering_cmd = 0.5236
        if steering_cmd <= -0.5236:
            steering_cmd = -0.5236
        if throttle_cmd >= 1:
            throttle_cmd = 1
        if throttle_cmd <= -1:
            throttle_cmd = -1
        # Direction of maneuver
        if direction =='ccw':
            steering_cmd = -steering_cmd # Negate steering command
        # Set control commands
        v_1.throttle_command = throttle_cmd # [-1, 1]
        v_1.steering_command = steering_cmd/0.5236 # [-1, 1]
        v_1.headlights_command = 1 # [0 = disabled, 1 = low beam, 2 = high beam]
        v_1.indicators_command = 0 # [0 = disabled, 1 = left turn indicator, 2 = right turn indicator, 3 = hazard indicator]
        # Publish control commands
        json_msg = v_1.generate_commands(verbose=False) # Generate vehicle 1 message
        try:
            sio.emit('Bridge', data=json_msg)
        except Exception as exception_instance:
            print(exception_instance)

################################################################################

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__) # Argument parser
    argparser.add_argument(
        '-m', '--maneuver',
        metavar='MANEUVER',
        dest='maneuver',
        choices = {'straight','skidpad','fishhook','slalom'},
        default='skidpad',
        help='select maneuver {straight, skidpad, fishhook, slalom}')
    argparser.add_argument(
        '-d', '--direction',
        metavar='DIRECTION',
        dest='direction',
        choices = {'cw','ccw'},
        default='ccw',
        help='select direction {cw, ccw}')
    argparser.add_argument(
        '-t', '--throttle',
        metavar='THROTTLE',
        dest='throttle',
        default=1,
        help='set throttle limit [-1, 1] norm%')
    argparser.add_argument(
        '-s', '--steering',
        metavar='STEERING',
        dest='steering',
        default=0.5236,
        help='set steering limit [0, 0.5236] rad')
    argparser.add_argument(
        '-tn', '--throttle_noise',
        metavar='THROTTLE_NOISE',
        dest='throttle_noise',
        default=0.0,
        help='set std dev for noisy throttle [0.001, 0.1] norm%')
    argparser.add_argument(
        '-sn', '--steering_noise',
        metavar='STEERING_NOISE',
        dest='steering_noise',
        default=0.0,
        help='set std dev for noisy steering [0.001, 0.1] rad')
    args = argparser.parse_args() # Parse the command line arguments (CLIs)
    t_start = time.time_ns() # Record starting time
    maneuver = args.maneuver # Load maneuver
    direction = args.direction # Load maneuver direction
    throttle = float(args.throttle) # Load throttle limit
    steering = float(args.steering) # Load steering limit
    throttle_noise = float(args.throttle_noise) # Load throttle std dev
    steering_noise = float(args.steering_noise) # Load steering std dev
    app = socketio.Middleware(sio, app) # Wrap flask application with socketio's middleware
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app) # Deploy as an eventlet WSGI server