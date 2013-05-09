from serial import Serial
import sys, os, curses


#board = Serial("/dev/ttyACM0", 115200)
#home()
# TODO: Add alias support
settings = {}
settings["xPos"] = float
settings["xIncrement"] = float
settings["yPos"] = float
settings["yIncrement"] = float
settings["zPos"] = float
settings["zIncrement"] = float
settings["zBuffer"] = float
settings["xMin"] = int
settings["xMax"] = int
settings["yMin"] = int
settings["yMax"] = int
settings["zMin"] = int
settings["zMax"] = int
settings["speed"] = int

increment = 100
speed = 2400
count = 0
lastCommand = None

xIncrement = 10
xPos = 0
yIncrement = 10
yPos = 0
zIncrement = 100.0
zPos = 364.4

zMin = 0
yMin = -70
xMin = -70
zMax = 364.4
yMax = 70
xMax = 70

zBuffer = 50

def home():
  gcode("G28") # Home every axis
  gcode("G91") # Set to relative positioning

def down():
  board.write("G1 Z%d F%d\n"%(self.increment, self.speed))
  print board.readline()
  board.write("M114\n")
  print board.readline()

# May want to change axis to point.
currentAxis = 'center'
zeroCalibrationPos = {}
zeroCalibrationPos['center'] = "X0 Y0"
zeroCalibrationPos['x'] = "X0 Y80"
zeroCalibrationPos['y'] = "X-30 Y48"
zeroCalibrationPos['z'] = "X0 Y0"
def prevAxis():
  global zeroCalibrationPos, currentAxis
  axes = {}
  axes['x'] = 'center'
  axes['y'] = 'x'
  axes['z'] = 'y'
  axes['center'] = 'z'
  currentAxis = axes[currentAxis]
  display("Switching to axis: " + currentAxis)
  gcode("g1 %s z%3.2f"%(zeroCalibrationPos[currentAxis], zBuffer))

def nextAxis():
  global zeroCalibrationPos, currentAxis
  axes = {}
  axes['center'] = 'x'
  axes['x'] = 'y'
  axes['y'] = 'z'
  axes['z'] = 'center'
  currentAxis = axes[currentAxis]
  display("Switching to axis: " + currentAxis)
  gcode("g90")
  gcode("g1 %s z%3.2f"%(zeroCalibrationPos[currentAxis], zBuffer))
  gcode("g91")

def display(msg, y=None, x=None, window=None):
  global stdscr
  if window == None: window=stdscr
  if y != None:
    window.addstr(y, 0, msg + "\n")
  else: window.addstr(msg + "\n")
  window.refresh()

def incrementZbuffer():
  """
  Need to fix increment amount and decrement amount.
  """
  zBuffer += 10

def decrementZbuffer():
  zBuffer -= 10

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
    moveToZ(zBuffer)
    while (zBuffer) <= zIncrement: incrementZdown()
    updateStats()
    return
  calibrationInProgress = True
  display("X Zero: %3.2f Y Zero: %3.2f"%(zeroPoints['x'], zeroPoints['y']), 5, window=stats)
  display("Z Zero: %3.2f C Zero: %3.2f"%(zeroPoints['z'], zeroPoints['center']), 6, window=stats)
  display("Starting calibrateZero. Will first home all axes and then move down to zBuffer from the bed.")
  home()
  moveToZ(zBuffer)
  while (zBuffer) <= zIncrement: incrementZdown()
  updateStats()
  # move down by progressively smaller increments
  display("Adjust zIncrement and then hit dot to continue.")
  while 1:
    c = stdscr.getch()
    if 10 == c:
      incrementZdown()
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
      incrementZup()
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
      decrementZbuffer()
    elif ord('B') == c:
      incrementZbuffer()
    elif 32 == c:
      zeroPoints[currentAxis] = zPos
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

def gcode(command):
  stdscr.addstr(command + "\n")
  #board.write(command + "\n")
  #return board.readline()

def moveXup():
  global xPos, lastCommand
  lastCommand = moveXup
  xPos += xIncrement
  gcode("G1 X%d F%d"%(xIncrement, speed))

def moveYup():
  global yPos, lastCommand
  lastCommand = moveYup
  yPos += yIncrement
  gcode("G1 Y%d F%d"%(yIncrement, speed))

def moveZup():
  global zPos, lastCommand
  lastCommand = moveZup
  zPos += zIncrement
  gcode("G1 Z%3.2f F%d"%(zIncrement, speed))

def moveXdown():
  global xPos, lastCommand
  lastCommand = moveXdown
  xPos -= xIncrement
  gcode("G1 X%d F%d"%(-xIncrement, speed))

def moveYdown():
  global yPos, lastCommand
  lastCommand = moveYdown
  yPos -= yIncrement
  gcode("G1 Y%d F%d"%(-yIncrement, speed))

def moveToZ(location):
  global zPos
  gcode("G90")
  zPos = location
  gcode("G1 Z%3.2f F%d"%(location, speed))
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
    offset = zIncrement
    while zIncrement > (zPos - offset) and zIncrement != 0.1: incrementZdown()
  if zPos - offset < -0.001: display("Not going below zero."); return
  zPos -= offset
  gcode("G1 Z%3.2f F%d"%(-offset, speed))

def speedUp():
  global speed
  speed += 100

def speedDown():
  global speed
  speed -= 100

zIncrementValues = [100, 50, 20, 10, 5, 1, 0.5, 0.2, 0.1]
zIncrementValueIndex = 0
def incrementZdown():
  global zIncrement, zIncrementValueIndex
  if zIncrementValueIndex == len(zIncrementValues) - 1: return
  zIncrementValueIndex = zIncrementValueIndex + 1
  zIncrement = zIncrementValues[zIncrementValueIndex]

def incrementZup():
  global zIncrement, zIncrementValueIndex
  if zIncrementValueIndex == 0: return
  zIncrementValueIndex = zIncrementValueIndex - 1
  zIncrement = zIncrementValues[zIncrementValueIndex]

def repeatLastCommand():
  global lastCommand
  lastCommand()

def updateStats():
  global stats
  #currentStats = gcode("M114")
  stats.addstr(0, 0, "X Pos : % 03d Y Pos : % 03d Z Pos : % 03.2f"%(xPos, yPos, zPos))
  stats.addstr(1, 0, "X Incr: % 03d Y Incr: % 03d Z Incr: % 03.2f"%(xIncrement, yIncrement, zIncrement))
  stats.addstr(2, 0, "Speed: % 04d"%(speed))
  stats.refresh()

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
def getSetCmdStatements(args):
  stmts = []
  (toktype, token, args) = getSetCmdToken(args)
  while 1:
    if toktype == TOKID:
      var = token
      (toktype, token, args) = getSetCmdToken(args)
      if toktype != TOKEQ:
        stmts.append((STMTVAL, var))
        continue
      (toktype, token, args) = getSetCmdToken(args)
      if toktype != TOKNUM:
        stmts.append((STMTERR, args))
        break
      val = token
      stmts.append((STMTSET, (var, val)))
      (toktype, token, args) = getSetCmdToken(args)
    elif token == None: break
    else: break
  return stmts

def getSetCmdCompletions(args):
  stmts = getSetCmdStatements(args)
  if len(stmts) == 0: return []
  print stmts
  (stype, var)=stmts[-1:][0]
  if stype == STMTVAL:
    i = args.find(var)
    return [args[:i] + n for n in settings.keys() if n.find(var) == 0]
  return []

def setCmd(args):
  """
  This is very hacky, but it works for now.
  """
  global settings, stdscr
  args = " ".join(args)
  args = args.split("=")
  name = args[0]
  if not settings.has_key(name):
    display("Unknown variable: " + name)
    return
  if len(args) == 1:
    # Display the value
    value = globals()[name]
    display(name + "=" + str(value))
  else:
    # Set the value
    value = settings[name](args[1])
    globals()[name] = value
    display(name + "=" + str(value))
  updateStats()

exCmds = {}
exCmds["set"] = setCmd
exCmds["calibrateZero"] = calibrateZero

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
        pass
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
cmds[chr(10)] = incrementZdown
cmds[';'] = incrementZup
cmds['q'] = lambda: sys.exit(0)

def deltaDactyl(ss):
  global stdscr, stats, status, maxx

  # Create left hand status area.
  (maxy, maxx) = ss.getmaxyx()
  stdscr = curses.newwin(maxy - 2, (maxx / 2) - 2, 0, 0)
  ss.refresh()
  stdscr.scrollok(1) # Allow it to scroll

  # Creat the stats area, get it to display, and hide the cursor.
  stats = curses.newwin(maxy/2, (maxx/2)+1, 0, (maxx/2)-1)
  curses.curs_set(0)
  updateStats()

  # Create the status area
  status = curses.newwin(2, maxx, maxy-2, 0)
  status.addstr(0, 0, " "*maxx, curses.A_REVERSE)
  status.keypad(1)
  status.refresh()
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
