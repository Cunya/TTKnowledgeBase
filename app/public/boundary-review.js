const players = new Map();
const attachPlayer = (iframe) => {
  if (!window.YT || players.has(iframe)) return;
  const start = Number(iframe.dataset.startSeconds || 0);
  const end = Number(iframe.dataset.endSeconds || 0);
  new window.YT.Player(iframe, { events: { onReady: (event) => players.set(iframe, { player: event.target, start, end }) } });
};
window.onYouTubeIframeAPIReady = () => document.querySelectorAll('iframe[data-video-id]').forEach(attachPlayer);
if (!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')) {
  const api = document.createElement('script'); api.src = 'https://www.youtube.com/iframe_api'; document.head.appendChild(api);
}
window.setInterval(() => players.forEach(({ player, start, end }) => {
  if (end > start && player.getCurrentTime() >= end - 0.15) { player.seekTo(start, true); player.playVideo(); }
}), 150);
