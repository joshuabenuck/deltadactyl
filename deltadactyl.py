from serial import Serial
import sys, os, curses, config

TOKID = 0; TOKNUM = 1; TOKEQ = 2; TOKNONE = 3
def parseIdentifier(args):
  token = ""
  while len(args) > 0:
    c = args[0]; args = args[1:]
    if c >= 'a' and c <= 'z':
      token+=c
    elif c >= 'A' and c <= 'Z':
      token+=c
    else:
      args=c+args
      break
  return (TOKID, token, args)

def parseNumber(args):
  token = ""
  while len(args) > 0:
    c = args[0]; args = args[1:]
    if c >= '0' and c <= '9':
      token+=c
    elif c == '.':
      token+=c
    else:
      args=c+args
      break
  return (TOKNUM, token, args)

def getSetCmdToken(args):
  token = ""
  while len(args) > 0:
    c = args[0]
    if c >= 'a' and c <= 'z':
      return parseIdentifier(args)
    elif c >= 'A' and c <= 'Z':
      return parseIdentifier(args)
    elif c >= '0' and c <= '9':
      return parseNumber(args)
    elif c == ' ':
      args = args[1:]
      continue
    elif c == '=':
      return (TOKEQ, "=", args[1:])
  return (TOKNONE, None, "")

STMTVAL = 0; STMTSET = 1; STMTERR = 2
class SetStmt(object):
  def __init__(self, id, var, value=None, error=None):
    self.id = id
    self.var = var
    self.value = value
    self.error = error

def getSetCmdStatements(args):
  stmts = []
  (toktype, token, args) = getSetCmdToken(args)
  while 1:
    if toktype == TOKID:
      var = token
      (toktype, token, args) = getSetCmdToken(args)
      if toktype != TOKEQ:
        stmts.append(SetStmt(STMTVAL, var))
        continue
      (toktype, token, args) = getSetCmdToken(args)
      if toktype != TOKNUM:
        stmts.append(SetStmt(STMTERR, error=args))
        break
      val = token
      stmts.append(SetStmt(STMTSET, var, val))
      (toktype, token, args) = getSetCmdToken(args)
    elif token == None: break
    else: break
  return stmts

class SingleValue(object):
  def __init__(self, cast, value):
    self.value = value
    self.cast = cast

  def __call__(self, newvalue=None):
    if newvalue != None:
      self.value = self.cast(newvalue)
    return self.value

  def __isub__(self, other):
    self.value -= other
    return self

  def __sub__(self, other):
    return self.value - other

  def __iadd__(self, other):
    self.value += other
    return self

  def __add__(self, other):
    return self.value + other

class SteppedValue(SingleValue):
  def __init__(self, values, cast, value=None, min=None, max=None):
    self.values = values
    self.value = value
    if value == None:
      self.value = self.values[0]
    SingleValue.__init__(self, cast, value)
    self.min = min
    self.max = max

  def find(self, value):
    if value in self.values:
      return self.values.index(value)
    return -1

  def up(self):
    index = self.find(self.value)
    if index == 0: return
    if index == -1:
      index = len(self.values)-1
      v = self.values[index]
      while self.value > v and index > 0:
        index -= 1
        v = self.values[index]
    else:
      index -= 1
    self.value = self.values[index]
    return self.value

  def down(self):
    index = self.find(self.value)
    if index == len(self.values) - 1: return
    if index == -1:
      index = 0
      v = self.values[index]
      maxIndex = len(self.values) - 1
      while self.value < v and index < maxIndex:
        index += 1
        v = self.values[index]
    else:
      index += 1
    self.value = self.values[index]
    return self.value

speed = SingleValue(int, config.speed)
count = 0
lastCommand = None

zMin = SingleValue(float, 0)
yMin = SingleValue(float, config.yMin)
xMin = SingleValue(float, config.xMin)
zMax = SingleValue(float, config.zMax)
yMax = SingleValue(float, config.yMax)
xMax = SingleValue(float, config.xMax)

zBuffer = SteppedValue([50, 25, 10, 5, 4, 3, 2, 1.5, 1, 0.5, 0.3, 0.2, 0.1, 0.0], float, config.zBuffer)

incrementValues = [10, 5, 1]
xIncrement = SteppedValue(incrementValues, float, config.xIncrement)
xPos = SingleValue(float, 0)
yIncrement = SteppedValue(incrementValues, float, config.yIncrement)
yPos = SingleValue(float, 0)
zIncrement = SteppedValue([100, 50, 20, 10, 5, 1, 0.5, 0.2, 0.1], float, 100.0)
zPos = SingleValue(float, config.zMax)

# TODO: Add alias support, populate automatically
settings = {}
def populateSettings():
  global settings
  vars = ["xPos", "xIncrement", "yPos", "yIncrement",
          "zPos", "zIncrement", "zBuffer", "xMin",
          "xMax", "yMin", "yMax", "zMin", "zMax", 
          "speed"]
  for var in vars:
    settings[var] = globals()[var]
populateSettings()

DEBUG = True
def gcode(command):
  command = command.upper()
  display(command)
  if DEBUG: return
  board.write(command + "\n")
  line = board.readline()
  display(line.strip())
  if line.find("ok") != 0:
    retval = line
  else: return line
  return retval

def home(args=None):
  global xPos, yPos, zPos
  gcode("G28") # Home every axis
  # The next line is commented out because it causes some
  # absolutely horrible problems.
  # All motion commands after issuing it are off.
  # Too many more uses of this and my belts are going to
  # be shot!
  #gcode("G92 Z% 3.2F"%zMax)
  gcode("G91") # Set to relative positioning
  zPos(zMax())
  xPos(yPos(0))

def m114(args=None):
  gcode("M114")

def g1(args):
  # TODO: Danger, danger! This can lead to bed crashes.
  # It needs to update the internal state and adjust the zIncrement,
  # but doesn't currently.
  gcode("G1 " + " ".join(args))

# May want to change axis to point.
currentAxis = 'center'
zeroCalibrationPos = {}
zeroCalibrationPos['center'] = (0, 0)
zeroCalibrationPos['x'] = (-60, -50)
zeroCalibrationPos['y'] = (63, -30)
zeroCalibrationPos['z'] = (0, 80)
def rotateAxis(axes):
  global zeroCalibrationPos, currentAxis
  currentAxis = axes[currentAxis]
  display("Switching to axis: " + currentAxis)
  gcode("G90")
  (x, y) = zeroCalibrationPos[currentAxis]
  gcode("G1 X%d Y%d Z%3.2f"%(x, y, zBuffer()))
  xPos(x)
  yPos(y)
  zPos(zBuffer())
  gcode("G91")

def prevAxis():
  axes = {'x':'center', 'y':'x', 'z':'y', 'center':'z'}
  rotateAxis(axes)

def nextAxis():
  axes = {'center':'x', 'x':'y', 'y':'z', 'z':'center'}
  rotateAxis(axes)

def display(msg, y=None, x=None, window=None):
  global stdscr
  if window == None: window=stdscr
  if y != None:
    window.addstr(y, 0, msg + "\n")
  else: window.addstr(msg + "\n")
  window.refresh()

def updateZincrement():
  global zBuffer, zIncrement
  while zBuffer() <= zIncrement(): zIncrement.down()

zeroPoints = {}
zeroPoints['x'] = 0
zeroPoints['y'] = 0
zeroPoints['z'] = 0
zeroPoints['center'] = 0
calibrationInProgress = False
# TODO: Add completion list decoration here...
def calibrateZero(args=None):
  """
  May want to rename to zeroCalibration to allow better cycling.
  Should use a command map to reduce verbosity.
  """
  global zeroPoints, currentAxis, stats, zIncrement, calibrationInProgress
  if calibrationInProgress:
    moveToZ(zBuffer())
    updateZincrement()
    updateStats()
    return
  calibrationInProgress = True
  display("X Zero: %3.2f Y Zero: %3.2f"%(zeroPoints['x'], zeroPoints['y']), 5, window=stats)
  display("Z Zero: %3.2f C Zero: %3.2f"%(zeroPoints['z'], zeroPoints['center']), 6, window=stats)
  display("Starting calibrateZero. Will first home all axes and then move down to zBuffer from the bed.")
  moveToZ(zBuffer())
  updateZincrement()
  updateStats()
  # move down by progressively smaller increments
  display("Adjust zIncrement and then hit dot to continue.")
  while 1:
    c = stdscr.getch()
    if 10 == c:
      zIncrement.down()
    elif ord('a') == c:
      display("Cycling through all axes.")
      nextAxis()
      nextAxis()
      nextAxis()
      nextAxis()
    elif ord(':') == c:
      # What to do here if calibrateZero is called again?
      exCommand()
    elif ord(';') == c:
      zIncrement.up()
    elif ord('J') == c:
      moveZdown()
    elif ord('K') == c:
      moveZup()
    elif ord('H') == c:
      prevAxis()
    elif ord('L') == c:
      nextAxis()
    elif ord('.') == c:
      repeatLastCommand()
    elif ord('b') == c:
      zBuffer.down()
    elif ord('B') == c:
      zBuffer.up()
    elif 32 == c:
      zeroPoints[currentAxis] = zPos()
    elif 27 == c or ord('q') == c:
      display("Exiting calibrateZero.")
      calibrationInProgress = False
      return
    else:
      display("Command ignored.")
    updateStats()

# go to 100, 50, 25, 10, 5, 4, 3, 2, 1, 0.5
# enter or . == previous movement command
# i == change increment
# gx, gy, gz == go to a specific location
# x, y, z == change position along given axis
# set xi yi zi
# set xlevel ylevel zlevel
# TODO: Implement saving / setting of level values.

def moveXup():
  global xPos, lastCommand
  lastCommand = moveXup
  xPos += xIncrement()
  gcode("G1 X%d F%d"%(xIncrement(), speed()))

def moveYup():
  global yPos, lastCommand
  lastCommand = moveYup
  yPos += yIncrement()
  gcode("G1 Y%d F%d"%(yIncrement(), speed()))

def moveZup():
  global zPos, lastCommand
  lastCommand = moveZup
  zPos += zIncrement()
  gcode("G1 Z%3.2f F%d"%(zIncrement(), speed()))

def moveXdown():
  global xPos, lastCommand
  lastCommand = moveXdown
  xPos -= xIncrement()
  gcode("G1 X%d F%d"%(-xIncrement(), speed()))

def moveYdown():
  global yPos, lastCommand
  lastCommand = moveYdown
  yPos -= yIncrement()
  gcode("G1 Y%d F%d"%(-yIncrement(), speed()))

def moveToZ(location):
  global zPos
  gcode("G90")
  zPos(location)
  updateZincrement()
  gcode("G1 Z%3.2f F%d"%(location, speed()))
  gcode("G91")

def moveZdown(offset=None):
  """
  Move Z down by one of the following amounts:
  - offset if passed in.
  - count if a prefix count was specified.
  - zIncrement, otherwise.
  Most other move commands need to handle similar fallback logic.
  Should repeating the last command use the current or previous zIncrement value?
  When should zIncrement automatically be adjusted?
  """
  global zPos, lastCommand, count
  lastCommand = moveZdown
  if offset != None: pass
  elif count != 0:
    offset = count
    count = 0
  else:
    offset = zIncrement()
    while zIncrement() > (zPos - offset) and zIncrement() != 0.1: zIncrement.down()
  if zPos - offset < -0.001: display("Not going below zero."); return
  zPos -= offset
  gcode("G1 Z%3.2f F%d"%(-offset, speed()))

# TODO: Replace with speed.up() and speed.down()
# Need another setting class. Perhaps IncrementedValue?
def speedUp():
  global speed
  speed += 100

def speedDown():
  global speed
  speed -= 100

def repeatLastCommand():
  global lastCommand
  lastCommand()

def updateStats():
  global stats
  #currentStats = gcode("M114")
  stats.addstr(0, 0, "X Pos : % 03d Y Pos : % 03d Z Pos : % 03.2f"%(xPos(), yPos(), zPos()))
  stats.addstr(1, 0, "X Incr: % 03d Y Incr: % 03d Z Incr: % 03.2f"%(xIncrement(), yIncrement(), zIncrement()))
  stats.addstr(2, 0, "Speed: % 04d"%(speed()))
  stats.addstr(3, 0, "Z Buffer: % 3.2F"%(zBuffer()))
  stats.addstr(4, 0, "X Min : % 03d Y Min : % 03d Z Min : % 03.2f"%(xMin(), yMin(), zMin()))
  stats.addstr(5, 0, "X Max : % 03d Y Max : % 03d Z Max : % 03.2f"%(xMax(), yMax(), zMax()))
  stats.addstr(6, 0, "X Zero: % 3.2f Y Zero: % 3.2f Z Zero: % 3.2f"%(
    zeroPoints["x"], zeroPoints["y"], zeroPoints["z"]))
  stats.addstr(7, 0, "C Zero: % 3.2f"%(zeroPoints["center"]))
  stats.refresh()
  config = open("config.py", "w")
  config.write("xIncrement = % 3.2F\n"%xIncrement())
  config.write("yIncrement = % 3.2F\n"%yIncrement())
  config.write("zIncrement = % 3.2F\n"%zIncrement())
  config.write("xMin = % 3.2F\n"%xMin())
  config.write("yMin = % 3.2F\n"%yMin())
  config.write("zMin = % 3.2F\n"%zMin())
  config.write("xMax = % 3.2F\n"%xMax())
  config.write("yMax = % 3.2F\n"%yMax())
  config.write("zMax = % 3.2F\n"%zMax())
  config.write("zBuffer = % 3.2F\n"%zBuffer())
  config.write("speed = %d\n"%speed())
  config.close()

def getSetCmdCompletions(args):
  stmts = getSetCmdStatements(args)
  if len(stmts) == 0: return []
  stmt=stmts[-1:][0]
  if stmt.id == STMTVAL:
    i = args.find(stmt.var)
    return ["set " + args[:i] + n for n in settings.keys() if n.find(stmt.var)==0]
  return []

completionFuncs = {}
def completion(tocall):
  def decorate(f):
    global completionFuncs
    completionFuncs[f.__name__] = tocall
    return f
  return decorate

@completion(tocall=getSetCmdCompletions)
def setCmd(args):
  """
  This is very hacky, but it works for now.
  TODO: Use parser in this function.
  """
  global settings, stdscr
  stmts = getSetCmdStatements(" ".join(args))
  for stmt in stmts:
    if stmt.id == STMTERR: continue
    if not settings.has_key(stmt.var):
      display("Unknown variable: " + stmt.var)
      continue
    if stmt.id == STMTVAL:
      # Display the value
      value = settings[stmt.var]()
    else:
      # Set the value
      settings[stmt.var](stmt.value)
      value = stmt.value
    display(stmt.var + "=" + str(value))
  updateStats()

exCmds = {}
exCmds["set"] = setCmd
exCmds["calibrateZero"] = calibrateZero
exCmds["home"] = home
exCmds["m114"] = m114
exCmds["g1"] = g1

exCmdHistory = []
exCmdIndex = 0

# TODO: Add left / right arrow support
def exCommand():
  """
  Lots to do here.
  - handling of arrow keys
  - tab completion of arguments
  - proper parsing of command arguments
  """
  global status, maxx, exCmdIndex
  status.addstr(1, 0, ":")
  curses.curs_set(1)
  cmdString = ""
  lastTabIndex = None
  currentMatch = None
  origCmd = None
  while 1:
    c = status.getch()
    if c == 10 or c == 27: # enter or escape
      # Save the current match
      if lastTabIndex != None: cmdString = currentMatch
      # Clear the command and hide the cursor
      status.addstr(1, 0, " "*(maxx-1))
      status.refresh()
      curses.curs_set(0)
      # On escape, return
      if c == 27: return
      # Otherwise, break out of the loop
      break
    elif c == curses.KEY_BACKSPACE or c == 127: # Backspace
      if lastTabIndex != None: cmdString = currentMatch
      lastTabIndex = None
      currentMatch = None
      if len(cmdString) == 0: continue
      (y, x) = status.getyx()
      cmdString = cmdString[:-1]
      status.delch(y, x-1)
    elif c == curses.KEY_UP:
      # Command history
      if exCmdIndex == 0: continue
      exCmdIndex = exCmdIndex - 1
      if origCmd == None: origCmd = cmdString
      cmdString = exCmdHistory[exCmdIndex]
      status.move(1,0)
      status.clrtoeol()
      status.addstr(":" + cmdString)
    elif c == curses.KEY_DOWN:
      if exCmdIndex == len(exCmdHistory): continue
      exCmdIndex = exCmdIndex + 1
      if exCmdIndex == len(exCmdHistory):
        cmdString = origCmd
      else:
        cmdString = exCmdHistory[exCmdIndex]  
      status.move(1,0)
      status.clrtoeol()
      status.addstr(":" + cmdString)
    elif c == ord('\t'):
      # Tab completion
      if cmdString.find(' ') == -1:
        names = exCmds.keys()
        matches = [n for n in names if n.find(cmdString) == 0]
        matches.append(cmdString)
        status.move(1,0)
        status.clrtoeol()
        if lastTabIndex == None: lastTabIndex = 0
        else: lastTabIndex = lastTabIndex + 1
        if len(matches) == lastTabIndex: lastTabIndex = 0
        currentMatch = matches[lastTabIndex]
        status.addstr(":" + currentMatch)
      else:
        # If we reach here, we have to complete a command argument.
        # TODO: Call tab completion decoration on command.
        # TODO: Figure out if this works with command history.
        parts = cmdString.split(" ")
        if len(parts) == 0: continue
        exCmdName = parts[0]
        if not exCmds.has_key(exCmdName): continue
        exCmd = exCmds[exCmdName]
        if not completionFuncs.has_key(exCmd.__name__): continue
        matches = completionFuncs[exCmd.__name__](" ".join(parts[1:]))
        matches.append(cmdString)
        status.move(1,0)
        status.clrtoeol()
        if lastTabIndex == None: lastTabIndex = 0
        else: lastTabIndex = lastTabIndex + 1
        if len(matches) == lastTabIndex: lastTabIndex = 0
        currentMatch = matches[lastTabIndex]
        status.addstr(":" + currentMatch)
    elif c > 256: continue
    else:
      if lastTabIndex != None: cmdString = currentMatch
      lastTabIndex = None
      currentMatch = None
      status.addstr(chr(c))
      cmdString = cmdString + chr(c)
  if cmdString in exCmdHistory:
    exCmdHistory.remove(cmdString)
  exCmdHistory.append(cmdString)
  exCmdIndex = len(exCmdHistory)
  parts = cmdString.split(" ")
  if exCmds.has_key(parts[0]):
    cmd = exCmds[parts[0]]
    cmd(parts[1:])
  else:
    stdscr.addstr("Unknown command: " + str(parts))

"""
This is a lot harder than it looks.
Need to figure out which cmd is selected and decide how modifying
the current cmd affects the history.
elif c == curses.KEY_LEFT:
  _, x = status.getyx()
  if x == 0: continue
  status.move(1, x - 1)
elif c == curses.KEY_RIGHT:
  _, x = status.getyx()
  # Not sure what the max should be.
  #if x == 0: continue
  status.move(1, x + 1)
"""

cmds = {}
cmds['h'] = moveXdown
cmds['j'] = moveYdown
cmds['k'] = moveYup
cmds['l'] = moveXup
cmds['J'] = moveZdown
cmds['K'] = moveZup

cmds['x'] = moveXup
cmds['y'] = moveYup
cmds['z'] = moveZup
cmds['X'] = moveXdown
cmds['Y'] = moveYdown
cmds['Z'] = moveZdown
cmds[':'] = exCommand
cmds['.'] = repeatLastCommand
cmds['s'] = speedDown
cmds['S'] = speedUp
cmds[chr(10)] = zIncrement.down
cmds[';'] = zIncrement.up
cmds['q'] = lambda: sys.exit(0)

def deltaDactyl(ss):
  global stdscr, stats, status, maxx, board

  # Create left hand status area.
  (maxy, maxx) = ss.getmaxyx()
  stdscr = curses.newwin(maxy - 2, (maxx / 2) - 2, 0, 0)
  ss.refresh()
  stdscr.scrollok(1) # Allow it to scroll

  # Create the stats area, get it to display, and hide the cursor.
  stats = curses.newwin(maxy/2, (maxx/2)+1, 0, (maxx/2)-1)
  curses.curs_set(0)

  # Create the status area
  status = curses.newwin(2, maxx, maxy-2, 0)
  status.addstr(0, 0, " "*maxx, curses.A_REVERSE)
  status.keypad(1)
  status.refresh()
  if not DEBUG:
    board = Serial("/dev/ttyACM0", 115200)
    line = ""
    while line.find("Using Default settings") == -1:
      line = board.readline()
      display(line.strip())
    home()
  updateStats()

  while 1:
    c = stdscr.getch()
    key = chr(c)
    if not cmds.has_key(key):
      stdscr.addstr(str(c) + "\n")
      stdscr.refresh()
      updateStats()
      continue
    cmd = cmds[key]
    (cury, curx) = curses.getsyx()
    cmd()
    stdscr.refresh()
    updateStats()
    #stdscr.addstr(cmd.__name__+"\n")

if __name__ == "__main__":
  curses.wrapper(deltaDactyl)
