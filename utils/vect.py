class Vect:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def hypot(self):
        if not polarP:
            self.hypot = hypot(x,y)
            self.direction = atan2(x,y)
        return self.hypot

    def direction(self):
        if not polarP:
            self.hypot = hypot(x,y)
            self.direction = atan2(x,y)
        return self.direction
