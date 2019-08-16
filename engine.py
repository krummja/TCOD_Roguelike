import tcod as libtcod

from components.fighter import Fighter
from components.inventory import Inventory
from death_functions import kill_monster, kill_player
from entity import Entity, get_blocking_entities_at_location
from fov_functions import initialize_fov, recompute_fov
from game_messages import Message, MessageLog
from game_states import GameStates
from input_handlers import handle_keys
from map_objects.game_map import GameMap
from render_functions import clear_all, render_all, RenderOrder

def main():

	# Console Parameters
	screen_width = 80
	screen_height = 50
	
	# GUI Parameters
	bar_width = 20
	panel_height = 7
	panel_y = screen_height - panel_height

    # Message Parameters
	message_x = bar_width + 2
	message_width = screen_width - bar_width - 2
	message_height = panel_height - 1

	# Map Parameters
	map_width = 80
	map_height = 43

	# Room Parameters
	room_max_size = 10
	room_min_size = 6
	max_rooms = 30

	# Field of View Parameters
	fov_algorithm = 0
	fov_light_walls = True
	fov_radius = 10
	
    # Spawn parameters
	max_monsters_per_room = 3
	max_items_per_room = 2

	# Tile Colors
	colors = {
		'dark_wall': libtcod.Color(0, 0, 100),
		'dark_ground': libtcod.Color(50, 50, 150),
		'light_wall': libtcod.Color(130, 110, 50),
		'light_ground': libtcod.Color(200, 180, 50)
		}

	# Entity Variables
	fighter_component = Fighter(
		hp=30, 
		defense=2, 
		power=5
		)
	inventory_component = Inventory(26)
	player = Entity(
		0, 
		0, 
		'@', 
		libtcod.white, 
		'Player', 
		blocks=True,
		render_order=RenderOrder.ACTOR,
		fighter=fighter_component,
		inventory=inventory_component
		)
	entities = [player]

	# Map Generator
	game_map = GameMap(         # defines the game map dimensions, calling GameMap class
		map_width, 
		map_height
		)
	game_map.make_map(          # generates the map
		max_rooms, 
		room_min_size, 
		room_max_size, 
		map_width, 
		map_height, 
		player, 
		entities, 
		max_monsters_per_room,
		max_items_per_room
		)
	
	fov_recompute = True
	fov_map = initialize_fov(game_map)

	# Console & GUI
	libtcod.console_set_custom_font('assets/arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
	libtcod.console_init_root(screen_width, screen_height, 'libtcod tutorial revised', False)
	con = libtcod.console_new(screen_width, screen_height)
	panel = libtcod.console_new(screen_width, panel_height)

	message_log = MessageLog(message_x, message_width, message_height)

	# Input Functions
	key = libtcod.Key()
	mouse = libtcod.Mouse()

	# Game States
	game_state = GameStates.PLAYERS_TURN
	previous_game_state = game_state

#############################################################
#                      MAIN GAME LOOP                       #
#############################################################

    # So long as the window is open, do...
	while not libtcod.console_is_window_closed():
		libtcod.sys_check_for_event(
			libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, 
			key, 
			mouse)

        # TRUE on Move, trigger recompute
		if fov_recompute:
			recompute_fov(
				fov_map, 
				player.x, 
				player.y, 
				fov_radius, 
				fov_light_walls, 
				fov_algorithm
				)

		# Render the frame
		render_all(
			con,
			panel,
			entities,
			player,
			game_map,
			fov_map,
			fov_recompute,
			message_log,
			screen_width, 
			screen_height,
			bar_width,
			panel_height,
			panel_y,
			mouse,
			colors,
			game_state
			)
		
        # Recompute FOV only on player move
		fov_recompute = False

		# Clean up the screen
		libtcod.console_flush()
		clear_all(
			con, 
			entities
			)

# INPUT HANDLERS

		action = handle_keys(key, game_state)
		move = action.get('move')
		pickup = action.get('pickup')
		show_inventory = action.get('show_inventory')
		drop_inventory = action.get('drop_inventory')
		inventory_index = action.get('inventory_index')
		exit = action.get('exit')
		fullscreen = action.get('fullscreen')

# Entity Turn Logics
		
    # PLAYER TURN
    
		# Combat Results
		player_turn_results = []        

        # Move
		if move and game_state == GameStates.PLAYERS_TURN:
			dx, dy = move
			destination_x = player.x + dx
			destination_y = player.y + dy

			if not game_map.is_blocked(destination_x, destination_y):
				target = get_blocking_entities_at_location(
					entities, 
					destination_x, 
					destination_y
					)

				if target:
					attack_results = player.fighter.attack(target)
					player_turn_results.extend(attack_results)
				else: 
					player.move(dx, dy)

					fov_recompute = True          
				# PASS TURN
				game_state = GameStates.ENEMY_TURN

		# Pickup
		elif pickup and game_state == GameStates.PLAYERS_TURN:
			for entity in entities:
				if entity.item and entity.x == player.x and entity.y == player.y:       # If item x,y == player x,y
					pickup_results = player.inventory.add_item(entity)
					player_turn_results.extend(pickup_results)
					
					break
				
			else:
				message_log.add_message(Message('There is nothing here to pick up.', libtcod.yellow))

		# Show Inventory
		if show_inventory:
			previous_game_state = game_state
			game_state = GameStates.SHOW_INVENTORY

		# Drop Inventory
		if drop_inventory:
			previous_game_state = game_state
			game_state = GameStates.DROP_INVENTORY

		# Inventory Index
		if inventory_index is not None and previous_game_state != GameStates.PLAYER_DEAD and inventory_index < len(
				player.inventory.items):
			item = player.inventory.items[inventory_index]

			if game_state == GameStates.SHOW_INVENTORY:
				player_turn_results.extend(player.inventory.use(item))
			elif game_state == GameStates.DROP_INVENTORY:
				player_turn_results.extend(player.inventory.drop_item(item))

        # ESC Key Logic
		if exit:
			if game_state in (GameStates.SHOW_INVENTORY, GameStates.DROP_INVENTORY):
				game_state = previous_game_state
			else:
				return True
		
        # Fullscreen
		if fullscreen:
			libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
		
		# Handling end of player turn
		for player_turn_result in player_turn_results:
			message = player_turn_result.get('message')
			dead_entity = player_turn_result.get('dead')
			item_added = player_turn_result.get('item_added')
			item_consumed = player_turn_result.get('consumed')
			item_dropped = player_turn_result.get('item_dropped')
			
			if message:
				message_log.add_message(message)
			
			if dead_entity:
				if dead_entity == player:
					message, game_state = kill_player(dead_entity)
				else:
					message = kill_monster(dead_entity)
				message_log.add_message(message)
				
			if item_added:
				entities.remove(item_added)
				game_state = GameStates.ENEMY_TURN
    
			if item_consumed:
				game_state = GameStates.ENEMY_TURN
    
			if item_dropped:
				entities.append(item_dropped)
    
				game_state = GameStates.ENEMY_TURN

    # ENEMY TURN
    
        # Handling the enemy turn
		if game_state == GameStates.ENEMY_TURN:
			for entity in entities:
				if entity.ai:
					enemy_turn_results = entity.ai.take_turn(
						player,
						fov_map,
						game_map,
						entities
					)
					
					for enemy_turn_result in enemy_turn_results:
						message = enemy_turn_result.get('message')
						dead_entity = enemy_turn_result.get('dead')
					
						if message:
							message_log.add_message(message)
							
						if dead_entity:
							if dead_entity == player:
								message, game_state = kill_player(dead_entity)
							else: 
								message = kill_monster(dead_entity)
								
							message_log.add_message(message)
							
							if game_state == GameStates.PLAYER_DEAD:
								break
							
					if game_state == GameStates.PLAYER_DEAD:
						break
					
			# Pass turn back to Player
			else:
				game_state = GameStates.PLAYERS_TURN

if __name__ == '__main__':
	main()