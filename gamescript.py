import utils

def setup(game):
    rm = game.hl_create_file("/readme.txt","Welcome to the fuse game. Try creating a file called 'answer.txt' in the secret folder.\n",0o444)
    rm.set_owner(0,0)
    sf = game.hl_mkdir("/secret",0o755)
    f = game.hl_create_file("/you_won.txt","You've done it. This is all the game there is so far.\n",0o444,True,0,0)
    fa = utils.Trigger.ready_function(utils.Node.node_available,"/secret/answer.txt",game)
    action = utils.Trigger.ready_function(f.show)
    cond = utils.Trigger.condition(fa,action)
    sf.add_trigger(utils.Event.NEW_CHILD,cond)
    forb = game.hl_mkdir("/forbidden",0o700)
    forb.set_owner(0,0)
