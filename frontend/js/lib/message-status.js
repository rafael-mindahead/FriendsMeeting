export function applyMessageStatus(message,status){
  if(!message||message.id!==status?.message_id)return false;
  if(status.delivered_at)message.delivered_at??=status.delivered_at;
  if(status.read_at){
    message.read_at??=status.read_at;
    message.delivered_at??=status.delivered_at;
  }
  return true;
}

export function mergeMessageStatus(previous,status){
  return {
    ...previous,
    ...status,
    delivered_at:status.delivered_at||previous?.delivered_at||null,
    read_at:status.read_at||previous?.read_at||null
  };
}

export function applyPendingMessageStatuses(messages,pendingStatuses){
  for(const message of messages){
    const status=pendingStatuses.get(message.id);
    if(status&&applyMessageStatus(message,status)){
      pendingStatuses.delete(message.id);
    }
  }
  return messages;
}
