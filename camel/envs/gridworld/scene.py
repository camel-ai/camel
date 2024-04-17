import random

from collections import deque
from llfbench.envs.gridworld.room import Room


class Scene:

    NORTH = "north"  # Action 0
    EAST = "east"    # Action 1
    WEST = "west"    # Action 2
    SOUTH = "south"  # Action 3
    DIRECTIONS = [NORTH, EAST, WEST, SOUTH]

    def __init__(self):
        self.rooms = []

        self.start_room = None
        self.goal_room = None

        self.room_ctr = dict()
        self.doors = dict()

        # Run BFS
        self.bfs_path = dict()

    def get_add_start_room(self, start_room):
        self.start_room = start_room

    def get_add_goal_room(self, goal_room):
        self.goal_room = goal_room

    def get_room(self, i):
        return self.rooms[i]

    def num_rooms(self):
        return len(self.rooms)

    def get_rooms(self):
        return self.rooms

    def get_start_room(self):
        return self.start_room

    def check_room_door(self, room, dir_to):

        if room in self.doors and dir_to in self.doors[room]:
            return self.doors[room][dir_to]
        else:
            return None

    def get_room_doors_description(self, room):

        s = " ".join([f"You have a door to the {dir_to} of you that takes you to the {ngbr_room.get_name()} room."
                     for dir_to, ngbr_room in self.doors[room].items()])
        return s

    def create_random_empty_room(self, pos):

        room_type = random.choice(Room.ROOM_TYPES)

        if room_type not in self.room_ctr:
            self.room_ctr[room_type] = 0

        self.room_ctr[room_type] += 1

        room = Room(room_type=room_type,
                    room_id=self.room_ctr[room_type],
                    pos=pos)
        self.rooms.append(room)
        self.doors[room] = dict()

        return room

    @staticmethod
    def opposite_direction(dir_to):

        if dir_to == Scene.NORTH:
            return Scene.SOUTH

        elif dir_to == Scene.SOUTH:
            return Scene.NORTH

        elif dir_to == Scene.WEST:
            return Scene.EAST

        elif dir_to == Scene.EAST:
            return Scene.WEST

        else:
            raise AssertionError(f"Direction {dir_to} is unhandled.")

    @staticmethod
    def check_pos_consistentcy(room, other_room, dir_to):
        # An additional check to see

        room_x, room_y = room.pos
        other_room_x, other_room_y = other_room.get_pos()

        if dir_to == Scene.NORTH:
            is_consistent = room_y < other_room_y

        elif dir_to == Scene.SOUTH:
            is_consistent = room_y > other_room_y

        elif dir_to == Scene.WEST:
            is_consistent = room_x > other_room_x

        elif dir_to == Scene.EAST:
            is_consistent = room_x < other_room_x

        else:
            raise AssertionError(f"Direction {dir_to} is unhandled.")

        return is_consistent

    @staticmethod
    def get_relative_pos(room, dir_to, length=1):

        room_x, room_y = room.pos

        if dir_to == Scene.NORTH:
            new_pos = (room_x, room_y + length)

        elif dir_to == Scene.SOUTH:
            new_pos = (room_x, room_y - length)

        elif dir_to == Scene.WEST:
            new_pos = (room_x - length, room_y)

        elif dir_to == Scene.EAST:
            new_pos = (room_x + length, room_y)

        else:
            raise AssertionError(f"Direction {dir_to} is unhandled.")

        return new_pos

    def add_door(self, room, dir_to, other_room):
        self.doors[room][dir_to] = other_room
        self.doors[other_room][self.opposite_direction(dir_to)] = room

    def start_bfs(self, start_room):

        queue = deque([])

        queue.append(start_room)
        self.bfs_path[start_room] = []

        while len(queue) > 0:

            room = queue.popleft()

            for dir_to, ngbr_room in self.doors[room].items():

                if ngbr_room not in self.bfs_path:

                    queue.append(ngbr_room)
                    path = list(self.bfs_path[room])
                    path.append((dir_to, ngbr_room))
                    self.bfs_path[ngbr_room] = path

        return self.bfs_path

    def get_optimal_path(self, room):

        # This is a path from this goal to this room
        # Path consists of [(action-1, room-1), (action-2, room-2), ...., (action-k, room-k)] where room-k=room
        path = self.bfs_path[room]

        # Compute path from current room to the goal
        optimal_path = list(reversed([(self.opposite_direction(direction), room_) for direction, room_ in path]))

        return optimal_path

    def get_gold_action(self, room):

        # This is a path from this goal to this room
        # Path consists of [(action-1, room-1), (action-2, room-2), ...., (action-k, room-k)] where room-k=room
        path = self.bfs_path[room]

        if len(path) == 0:  # No action to take
            gold_direction = None
        else:
            direction, room_ = path[-1]
            assert room_ == room
            # We need to in opposite direction
            gold_direction = self.opposite_direction(direction)

        return gold_direction

    def log_scene(self, logger):

        logger.log(f"Start room {self.start_room.get_name()} and Key room {self.goal_room.get_name()}\n")

        for room in self.rooms:
            objects = room.get_objects()
            if len(objects) == 0:
                logger.log(f"Room {room.get_name()}: containing no objects.")
            else:
                obj_names = ", ".join(objects)
                logger.log(f"Room {room.get_name()}: containing objects {obj_names}")
            for dir_to, new_room in self.doors[room].items():
                logger.log(f"\t - Taking {dir_to} path leads to {new_room.get_name()}.")
            logger.log("\n\n")
