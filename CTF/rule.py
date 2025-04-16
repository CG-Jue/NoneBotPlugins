from nonebot.adapters.onebot.v11 import Event


async def checkIfListenpro(event: Event) -> bool:

    # global 391680981
     
    templist = [391680981,936493920] 
    if event.get_event_name() == "message.group.normal":
        for id in templist:
            if id == event.group_id:
                return True
            return False
    
    return False


async def check_if_403(event: Event) -> bool:

    # global 391680981
    forbiddenGroup = [445629724]
     
    if event.get_event_name() == "message.group.normal":
        ## 所有功能只支持群聊
        for id in forbiddenGroup:
            ## 被禁止的群聊不能使用
            if id == event.group_id:
                return False
            return True
    
    return False
