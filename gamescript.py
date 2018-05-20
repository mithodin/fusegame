import utils

def setup(game):
    game.hl_create_file("/readme.txt","Welcome to the fuse game. Try creating a file called 'answer.txt' in the secret folder.\n",0o000)
    sf = game.hl_mkdir("/secret",0o755)
    f = game.hl_create_file("/hello.txt","You've done it. This is all the game there is so far.\n",0o600,True)
    fa = utils.Node.get_node_available("/secret/answer.txt",game)
    action = f.get_show()
    cond = utils.Trigger.condition(fa,action)
    sf.add_trigger(utils.Event.NEW_CHILD,cond)
