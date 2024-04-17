class Room:

    ROOM_TYPES = ["kitchen", "bedroom", "lobby", "toilet", "balcony", "corridor", "drawing room"]
    OBJECTS = ["lamp", "table", "couch", "television", "fridge"]
    goal = "treasure"

    def __init__(self, room_type, room_id, pos, max_objects=2):
        """
        :param room_type: type of the room from Room.ROOM_TYPES
        :param room_id: a number to distinguish between multiple rooms with the same ID
        :param pos: (x, y) pair where x is the horizontal axis with west towards -infinity and east towards +infinity
                    and y is the vertical axis with north towards +infinity and south towards -infinity.
        """

        assert room_type in Room.ROOM_TYPES, \
            f"room_type {room_type} must be one of the following types {Room.ROOM_TYPES}"
        assert type(pos) == tuple and len(pos) == 2, "Position is a tuple containing (x, y)"

        self.room_type = room_type
        self.room_id = room_id
        self.pos = pos
        self.name = f"{self.room_type}-{room_id}"

        self.max_objects = max_objects
        self.objects = []

    def get_name(self):
        return self.name

    def get_objects(self):
        return self.objects

    def describe_room(self):
        s = f"You are in {self.name} room. "

        if len(self.objects) > 0:
            s += "This room has following objects: " + ",".join(self.objects) + ". "

        return s

    def get_pos(self):
        return self.pos

    def add_goal(self):
        self.objects.append(Room.goal)

    def add_object(self, obj):

        if len(self.objects) < self.max_objects:
            self.objects.append(obj)
        else:
            raise AssertionError(f"Cannot add more than {self.max_objects} to {self.name}")
