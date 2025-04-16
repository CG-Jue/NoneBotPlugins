from nonebot.adapters.onebot.v11 import Event,GroupMessageEvent


async def checkIfListenpro(event: GroupMessageEvent):

     
    templist = [445629724,391680981,915938735] # 群号列表
    if event.get_event_name() == "message.group.normal":

    
        for id in templist:
            if id == event.group_id:
                return True
            return False
    return False



async def checkIfWWD(event: GroupMessageEvent):

    
    # print('======')
    # print(event.get_type())
    # print(event.get_event_name())
    # print(event.get_event_description())
    templist = [629590326] # 群号列表
   
    if event.get_event_name() == "message.group.normal":

        for id in templist:
            if id == event.group_id:
                return True
            return False
    return False

