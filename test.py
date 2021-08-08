import big2Game
import enumerateOptions
from PPONetwork import PPONetwork, PPOModel

import threading
import json
import numpy as np
from flask import Flask
from datetime import datetime
#import tensorflow as tf
import tensorflow.compat.v1 as tf
tf.disable_eager_execution()
tf.disable_v2_behavior()
import joblib
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

RANGE4 = [1,2,3,4]
TIMER = 3
app = Flask(__name__)
game = big2Game.big2Game()
#enterList = {}
#readyList = {}
seats = [False]*5
started = False
state_n = 0
playerNetworks = {}
playerModels = {}

def setInterval(func, sec):
    def func_wrapper():
        setInterval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

def network():
    inDim = 412
    outDim = 1695
    entCoef = 0.01
    valCoef = 0.5
    maxGradNorm = 0.5
    sess = tf.Session()
    playerNetworks[1] = PPONetwork(sess, inDim, outDim, "p1Net")
    playerNetworks[2] = PPONetwork(sess, inDim, outDim, "p2Net")
    playerNetworks[3] = PPONetwork(sess, inDim, outDim, "p3Net")
    playerNetworks[4] = PPONetwork(sess, inDim, outDim, "p4Net")
    playerModels[1] = PPOModel(sess, playerNetworks[1], inDim, outDim, entCoef, valCoef, maxGradNorm)
    playerModels[2] = PPOModel(sess, playerNetworks[2], inDim, outDim, entCoef, valCoef, maxGradNorm)
    playerModels[3] = PPOModel(sess, playerNetworks[3], inDim, outDim, entCoef, valCoef, maxGradNorm)
    playerModels[4] = PPOModel(sess, playerNetworks[4], inDim, outDim, entCoef, valCoef, maxGradNorm)
    tf.global_variables_initializer().run(session=sess)
    params = joblib.load("modelParameters136500")
    playerNetworks[1].loadParams(params)
    playerNetworks[2].loadParams(params)
    playerNetworks[3].loadParams(params)
    playerNetworks[4].loadParams(params)

def newPolling():
    global state_n
    state_n += 1

@app.route("/polling/<id>")
def polling(id):
    #id = int(id)
    global state_n
    return str(state_n)

@app.route("/")
def index():
    return "Hello Big2!"
    
@app.route("/enter/<id>")
def enter(id):
    id = int(id)
    if (started): return ''
    seats[id] = True
    #if (enterList[id]): return
    #enterList[id] = True
    #readyList[id] = False
    #seats[id-1].time = datetime.now()
    #printSeats()
    #newPolling()
    return ''

@app.route("/ready/<id>")
def ready(id):
    id = int(id)
    global started
    if (started): return
    readyList[id] ^= True
    n_enter = sum([enterList[i] for i in RANGE4])
    n_ready = sum([readyList[i] for i in RANGE4])
    if (n_enter == n_ready and n_enter != 0):
        started = True
        game.reset()
        newPolling()
    printSeats()
    newPolling()
    return ''

@app.route("/start")
def start():
    gameStart()
    return ''

@app.route("/reset")
def reset():
    gameReset()
    return ''

@app.route("/data/<id>")
def data(id):
    id = int(id)
    if (not started):
        return json.dumps({
            'state': 'wait', 
            #'enter': [enterList[i] for i in RANGE4],
            #'ready': [readyList[i] for i in RANGE4],
        })
    hands = [game.currentHands[i].tolist() for i in RANGE4]
    hands = [e if i == id else [-1]*len(e) for i,e in zip(RANGE4,hands)]
    options = actionsToOptions(game.returnAvailableActions()) if game.playersGo == id else []
    return json.dumps({
        'state': 'over' if game.gameOver else 'game',
        'player': game.playersGo,
        'top': game.handsPlayed[game.goIndex-1].hand.tolist(),
        'options': options,
        'hands': hands,
    })

@app.route("/play/<id>/<option>")
def play(id, option):
    global game, state_n
    (ind, nC) = optionToIndex(json.loads(option))
    game.updateGame(ind, nC)
    if (game.gameOver): gameOver()
    newPolling()
    printGame()
    _playAi()
    return ''

@app.route("/playai")
def playAi():
    if (not started): return ''
    if (game.gameOver): return ''
    if (seats[game.playersGo]): return ''
    go, state, actions = game.getCurrentState()
    a, v, nlp = playerNetworks[go].step(state, actions)
    ind, nC = (-1, 0) if (a == enumerateOptions.passInd) else enumerateOptions.getOptionNC(a[0])
    game.updateGame(ind, nC)
    if (game.gameOver): gameOver()
    newPolling()
    printGame()
    _playAi()
    return ''

def _playAi():
    threading.Timer(TIMER, playAi).start()

def actionsToOptions(actions):
    options = []
    for i in range(len(actions)):
        if actions[i] == 1:
            options.append(indexToOption(i))
    return options

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

def printGame():
    for i in RANGE4:
        hands = game.currentHands[i].tolist()
        actions = actionsToOptions(game.returnAvailableActions()) if game.playersGo == i else ''
        print(hands, actions)
    print()

def printSeats():
    print(enterList, readyList)

def gameStart():
    global started
    started = True
    game.reset()
    _playAi()
    newPolling()

def gameReset():
    global started
    for i in RANGE4: seats[i] = False
    #for i in RANGE4: enterList[i] = False
    #for i in RANGE4: readyList[i] = False
    started = False
    newPolling()

def gameOver():
    None

def main():
    network()
    gameReset()
    app.run(host='0.0.0.0', port=80)

main()
