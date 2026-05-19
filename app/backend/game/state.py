## Game state here (verification with server)

## import something that generates a map first

import scipy

class GameState:
  def __init__(self, seed, grid):
    self.seed = seed
    self.grid = [[]]

class Tile:
  def __init__(self, x, z, terrain, is_trap, is_occupied, faction)
    self.x = x
    self.z = z
    self.terrain = terrain
    self.is_trap = False
    self.is_occupied = False
    self.faction = ""
    
class Outpost:
  def __init__(self, income, faction, hp)
    self.income = 100
    self.faction = ""
    self.current_hp = hp
    self.hp = hp

  
    
    
  
