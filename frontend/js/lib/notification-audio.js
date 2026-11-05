const audioContextConstructor = () => globalThis.AudioContext||globalThis.webkitAudioContext;
const audioEventStorageKey = "friendsmeeting.notifications.played";
const recentEventLimit = 100;
let audioContext;
const claimedInThisTab = new Set();

export function notificationVolume(preferences,senderId) {
  if(!preferences||preferences.muted||preferences.volume===0)return 0;
  const sender=preferences.senders?.find(item=>item.user_id===senderId);
  if(sender?.muted)return 0;
  const factor=Number.isInteger(sender?.volume_factor)?sender.volume_factor:100;
  return Math.round(preferences.volume*factor/100);
}

export async function claimNotificationSound(eventId) {
  if(typeof eventId!=="string"||!eventId||claimedInThisTab.has(eventId))return false;

  const claim=()=>{
    let recent=[];
    try {
      recent=JSON.parse(localStorage.getItem(audioEventStorageKey)||"[]");
      if(!Array.isArray(recent))recent=[];
    } catch(error) {
      console.warn("Não foi possível ler os eventos sonoros recentes.",error);
    }
    if(recent.some(item=>item.id===eventId&&Date.now()-item.at<60000))return false;
    recent=recent.filter(item=>item&&typeof item.id==="string"&&Date.now()-item.at<60000);
    recent.push({id:eventId,at:Date.now()});
    try {
      localStorage.setItem(audioEventStorageKey,JSON.stringify(recent.slice(-recentEventLimit)));
    } catch(error) {
      console.warn("Não foi possível compartilhar a deduplicação de áudio entre abas.",error);
    }
    return true;
  };

  let claimed;
  if(globalThis.navigator?.locks?.request) {
    claimed=await navigator.locks.request(
      "friendsmeeting-notification-sound",
      claim
    );
  } else {
    claimed=claim();
  }
  if(!claimed)return false;
  claimedInThisTab.add(eventId);
  if(claimedInThisTab.size>recentEventLimit) {
    claimedInThisTab.delete(claimedInThisTab.values().next().value);
  }
  return true;
}

export async function playNotificationSound(volumePercent) {
  if(!Number.isFinite(volumePercent)||volumePercent<=0)return false;
  const AudioContext=audioContextConstructor();
  if(!AudioContext)return false;
  audioContext??=new AudioContext();
  if(audioContext.state==="suspended") {
    try {
      await audioContext.resume();
    } catch(error) {
      if(error instanceof DOMException&&error.name==="NotAllowedError")return false;
      throw error;
    }
  }
  if(audioContext.state!=="running")return false;

  const now=audioContext.currentTime;
  const output=audioContext.createGain();
  output.gain.value=Math.min(1,volumePercent/100)*0.18;
  output.connect(audioContext.destination);

  for(const [offset,frequency] of [[0,740],[0.12,988]]) {
    const oscillator=audioContext.createOscillator();
    const envelope=audioContext.createGain();
    oscillator.type="sine";
    oscillator.frequency.value=frequency;
    envelope.gain.setValueAtTime(0,now+offset);
    envelope.gain.linearRampToValueAtTime(0.65,now+offset+0.015);
    envelope.gain.exponentialRampToValueAtTime(0.001,now+offset+0.16);
    oscillator.connect(envelope);
    envelope.connect(output);
    oscillator.start(now+offset);
    oscillator.stop(now+offset+0.17);
  }
  return true;
}
