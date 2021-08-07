import big2Game
import enumerateOptions
import json
import numpy as np
from flask import Flask
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

game = big2Game.big2Game()
client_n = 0
ready_list = [False]*5
started = False
state_n = 0

@app.route("/")
def index():
    return "Hello Big2!"
    
@app.route("/enter/<id>")
def enter(id):
    global client_n
    client_n += 1
    print('id', id)
    return ''

@app.route("/ready/<id>")
def ready(id):
    global client_n, ready_list, started, state_n
    ready_list[int(id)] ^= True
    print('ready', ready_list)
    if (ready_list.count(True) == client_n):
        started = True
        state_n += 1
        game.reset()
    return ''

@app.route("/reset")
def reset():
    global game
    game.reset()
    return ""

@app.route("/state")
def state():
    global state_n
    return str(state_n)

@app.route("/data/<id>")
def data(id):
    global game, started
    return json.dumps({
        'started': started, 
        'gameOver': game.gameOver, 
        'playersGo': game.playersGo,
        'handsPlayed': game.handsPlayed[game.goIndex-1].hand.tolist(),
        'availableActions': parseActions(game.returnAvailableActions()) if game.playersGo == int(id) else [],
        'currentHands': game.currentHands[int(id)].tolist(),
        'currentHandsCount': [len(game.currentHands[i]) for i in [1,2,3,4]]
    })

@app.route("/play/<id>/<option>")
def play(id, option):
    global game, state_n
    (ind, nC) = optionToIndex(json.loads(option))
    game.updateGame(ind, nC)
    state_n += 1
    return ''

def parseActions(actions):
    parsed = []
    for i in range(len(actions)):
        if actions[i] == 1:
            parsed.append(indexToOption(i))
    return parsed

def indexToOption(index):
    (ind, nC) = enumerateOptions.getOptionNC(index)
    option = []
    if ind == -1:
        option = []
    elif nC == 1:
        option = [ind]
    elif nC == 2:
        option = (enumerateOptions.inverseTwoCardIndices[ind]).tolist()
    elif nC == 3:
        option = (enumerateOptions.inverseThreeCardIndices[ind]).tolist()
    elif nC == 4:
        option = (enumerateOptions.inverseFourCardIndices[ind]).tolist()
    elif nC == 5:
        option = (enumerateOptions.inverseFiveCardIndices[ind]).tolist()
    return option

def optionToIndex(option):
    (ind, nC) = -1, len(option)
    if nC == 0:
        ind = -1
    elif nC == 1:
        ind = option[0]
    elif nC == 2:
        ind = enumerateOptions.twoCardIndices[option[0]][option[1]]
    elif nC == 3:
        ind = enumerateOptions.threeCardIndices[option[0]][option[1]][option[2]]
    elif nC == 4:
        ind = enumerateOptions.fourCardIndices[option[0]][option[1]][option[2]][option[3]]
    elif nC == 5:
        ind = enumerateOptions.fiveCardIndices[option[0]][option[1]][option[2]][option[3]][option[4]]
    return (ind, nC)

app.run(host='127.0.0.1', port=80)
