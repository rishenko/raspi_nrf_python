# Raspberry Pi nRF24L01+ Cascade System
One part server that can receive communications from nRF24L01+ transceivers,
marshal and unmarshal into JSON and python objects and serve them up to
an open port. Another part of the project is are standalone servers that
act as pubsubs to remote ports, aggregate the JSON payload, convert to
python, perform any necessary logic, and broadcast on another port for
any listeners.

The idea is to have a series of Rpi devices listening to nRF transceivers,
broadcast to any subscribing gateways, you can then refine the data and
rebroadcast to any listeners. This allows a full pubsub network to
aggregate and rebroadcast data received from the nrf devices.

## Current Status
This project served as a testbed for playing with python and Twisted, becoming
more and more familiar with nRF devices and Raspberry Pi interactions. It is
currently inactive and will likely be converted to Elixir Nerves sometime soon.
