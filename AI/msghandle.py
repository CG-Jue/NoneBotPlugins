from nonebot import logger



def msghd(success:bool, result:str) -> tuple[bool,str]:

    """
    对ai生成的结果进行人工处理

    """
    if success and isinstance(result, str) and "【" in result and "】" in result:
        try:
            # Extract the content and intensity
            start_idx = result.find("【")
            end_idx = result.find("】", start_idx)
            if start_idx != -1 and end_idx != -1:
                content = result[start_idx+1:end_idx]  # Extract content between 【】
                
                # Extract the intensity value
                intensity = 0
                if '「' in result and '」' in result:
                    start_intensity = result.find("「", end_idx)
                    end_intensity = result.find("」", start_intensity)
                    if start_intensity != -1 and end_intensity != -1:
                        try:
                            intensity = int(result[start_intensity+1:end_intensity])
                        except ValueError:
                            pass
                
                # If intensity is below threshold, don't send the message
                if intensity < 60:
                    success = False
                else:
                    # Set result to just the content without the tags
                    result = content
        except Exception as e:
            logger.debug(f"处理七七的话时出错: {e}")
        return success, result
    return False, "null"