import utils

def setup(game):
    sf = game.hl_mkdir("/secret",0o755)
    f = game.hl_create_file("/hallo.txt","Hallo Welt\n",0o600,True)
    fa = utils.Node.get_node_available("/secret/answer.txt",game)
    action = f.get_show()
    cond = utils.Trigger.condition(fa,action)
    sf.add_trigger(utils.Event.NEW_CHILD,cond)
