#!/usr/bin/env python

"""A simple Multi-User Dungeon (MUD) game. Players can talk to each
other, examine their surroundings and move between rooms.

Some ideas for things to try adding:
	* More rooms to explore
	* An 'emote' command e.g. 'emote laughs out loud' -> 'Mark laughs
		out loud'
	* A 'whisper' command for talking to individual players
	* A 'shout' command for yelling to players in all rooms
	* Items to look at in rooms e.g. 'look fireplace' -> 'You see a
		roaring, glowing fire'
	* Items to pick up e.g. 'take rock' -> 'You pick up the rock'
	* Monsters to fight
	* Loot to collect
	* Saving players accounts between sessions
	* A password login
	* A shop from which to buy items

author: Mark Frimston - mfrimston@gmail.com
"""

import time
from pathlib import Path
import hjson
from termcolor import colored

# import the MUD server class
from mudserver import MudServer


# CONFIG
STARTING_ROOM = "tavern"


def fmtPlayerName(playerName: str) -> str:
	return colored(playerName, "yellow")


def fmtRoomName(roomName: str) -> str:
	return colored(roomName, "green")


def fmtRoomDescription(roomDesc: str) -> str:
	return roomDesc + "\n"


def fmtLook(room: dict) -> str:
	return fmtRoomName(room["name"]) + "\n\r" + room["description"].strip()


def getPlayerRoomID(id: int):
	return players[id]["room"]


def getPlayerRoom(id: int) -> dict:
	return rooms[getPlayerRoomID(id)]


def setPlayerRoom(id: int, roomID: str) -> dict:
	players[id]["room"] = roomID
	return rooms[roomID]


# structure defining the rooms in the game. Try adding more rooms to the game!
rooms = hjson.loads(Path("data/rooms.hjson").read_text())

# stores the players in the game
players = {}

# start the server
mud = MudServer()


def processNewPlayers():
	for id in mud.get_new_players():
		# add the new player to the dictionary, noting that they've not been
		# named yet.
		# The dictionary key is the player's id number. We set their room to
		# None initially until they have entered a name
		# Try adding more player stats - level, gold, inventory, etc
		players[id] = {
			"name": None,
			"room": None,
		}

		# send the new player a prompt for their name
		mud.send_message(id, "What is your name?")


def processDisconnectedPlayers():
	for id in mud.get_disconnected_players():
		# if for any reason the player isn't in the player map, skip them and
		# move on to the next one
		if id not in players:
			continue

		# go through all the players in the game
		for pid, pl in players.items():
			# send each player a message to tell them about the diconnected
			# player
			mud.send_message(pid, f"{fmtPlayerName(players[id]['name'])} quit the game")

		# remove the player's entry in the player dictionary
		del(players[id])


def welcomeNewPlayer(id, command):
	players[id]["name"] = command
	players[id]["room"] = STARTING_ROOM

	# go through all the players in the game
	for pid, pl in players.items():
		# send each player a message to tell them about the new player
		mud.send_message(pid, f"{fmtPlayerName(players[id]['name'])} entered the game")

	# send the new player a welcome message
	mud.send_message(id, f"Welcome to the game, {fmtPlayerName(players[id]['name'])}. "
						+ "Type 'help' for a list of commands. Have fun!")

	# send the new player the description of their current room
	mud.send_message(id, fmtLook(getPlayerRoom(id)))


def printHelp(id):
	# send the player back the list of possible commands
	mud.send_message(id, "Commands:")
	mud.send_message(id, "  say <message>  - Says something out loud, "
							+ "e.g. 'say Hello'")
	mud.send_message(id, "  look           - Examines the "
							+ "surroundings, e.g. 'look'")
	mud.send_message(id, "  go <exit>      - Moves through the exit "
							+ "specified, e.g. 'go outside'")


def cmdSay(id, params):
	# go through every player in the game
	for pid, pl in players.items():
		# if they're in the same room as the player
		if players[pid]["room"] == players[id]["room"]:
			# send them a message telling them what the player said
			mud.send_message(pid, "{} says: {}".format(fmtPlayerName(players[id]["name"]), params))


def cmdLook(id):
	# store the player's current room
	rm = getPlayerRoom(id)

	# send the player back the description of their current room
	mud.send_message(id, fmtLook(rm))

	playershere = []
	# go through every player in the game
	for pid, pl in players.items():
		# if they're in the same room as the player
		if players[pid]["room"] == rm:
			# ... and they have a name to be shown
			if players[pid]["name"] is not None:
				# add their name to the list
				playershere.append(fmtPlayerName(players[pid]["name"]))

	# send player a message containing the list of players in the room
	mud.send_message(id, "Players here: {}".format(", ".join(playershere)))

	# send player a message containing the list of exits from this room
	mud.send_message(id, "Exits are: {}".format(", ".join(rm["exits"])))


def cmdGo(id, params):
	# store the exit name
	ex = params.lower()

	# store the player's current room
	rm = getPlayerRoom(id)

	# if the specified exit is found in the room's exits list
	if ex in rm["exits"]:

		# go through all the players in the game
		for pid, pl in players.items():
			# if player is in the same room and isn't the player
			# sending the command
			if players[pid]["room"] == players[id]["room"] \
					and pid != id:
				# send them a message telling them that the player
				# left the room
				mud.send_message(pid, "{} left via exit '{}'".format(fmtPlayerName(players[id]["name"]), ex))

		# update the player's current room to the one the exit leads to
		rm = setPlayerRoom(id, rm["exits"][ex])

		# go through all the players in the game
		for pid, pl in players.items():
			# if player is in the same (new) room and isn't the player
			# sending the command
			if players[pid]["room"] == players[id]["room"] \
					and pid != id:
				# send them a message telling them that the player
				# entered the room
				mud.send_message(pid, "{} arrived via exit '{}'".format(fmtPlayerName(players[id]["name"]), ex))

		# send the player a message telling them where they are now
		mud.send_message(id, "You arrive at '{}'".format(fmtRoomName(rm["name"])))

	# the specified exit wasn't found in the current room
	else:
		# send back an 'unknown exit' message
		mud.send_message(id, f"Unknown exit '{ex}'")


print("Server starting...")


# main game loop. We loop forever (i.e. until the program is terminated)
while True:
	# pause for 1/5 of a second on each loop, so that we don't constantly
	# use 100% CPU time
	time.sleep(0.2)

	# 'update' must be called in the loop to keep the game running and give
	# us up-to-date information
	mud.update()

	# go through any newly connected players
	processNewPlayers()

	# go through any recently disconnected players
	processDisconnectedPlayers()

	# go through any new commands sent from players
	for id, command, params in mud.get_commands():

		# if for any reason the player isn't in the player map, skip them and
		# move on to the next one
		if id not in players:
			continue

		# if the player hasn't given their name yet, use this first command as
		# their name and move them to the starting room.
		if players[id]["name"] is None:
			welcomeNewPlayer(id, command)

		# each of the possible commands is handled below. Try adding new
		# commands to the game!

		# 'help' command
		elif command == "help":
			printHelp(id)

		# 'say' command
		elif command == "say":
			cmdSay(id, params)

		# 'look' command
		elif command == "look" or command == "l":
			cmdLook(id)

		# 'go' command
		elif command == "go":
			cmdGo(id, params)

		# some other, unrecognised command
		else:
			# send back an 'unknown command' message
			mud.send_message(id, f"Unknown command '{command}'")
