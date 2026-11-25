import {loadImage, request} from './api.js';

const button = document.querySelector('#play');
const seek = document.querySelector('#seek');
const canvas = document.querySelector('#projection');
const paint = canvas.getContext('2d');
const empty = document.querySelector('#projection-empty');
const label = document.querySelector('#playhead');
const blend = document.querySelector('#blend');
const summary = document.querySelector('#plan-summary');

let context, node, animation, media, anchor, position;
let generation = 0;

function frameAt(boundaries, sample) {
  let first = 0;
  let last = boundaries.length - 1;
  while (last - first > 1) {
    const mid = (first + last) >>> 1;
    if (boundaries[mid] <= sample) first = mid;
    else last = mid;
  }
  return first;
}

function render(index) {
  const {atlas, plan} = media.info;
  const page = Math.floor(index / atlas.per_sheet);
  const cell = index % atlas.per_sheet;
  const x = cell % atlas.columns * atlas.tile_width;
  const y = Math.floor(cell / atlas.columns) * atlas.tile_height;
  paint.drawImage(media.pages[page], x, y, atlas.tile_width, atlas.tile_height, 0, 0, canvas.width, canvas.height);
  seek.value = index;
  const shot = plan.frames[index];
  label.textContent = `${index + 1} / ${plan.frame_count} 格 · 源 ${shot.tail}${shot.head === null ? '' : ` ↔ ${shot.head}`}`;
  blend.hidden = shot.head === null;
}

function currentPosition() {
  if (!node) return position;
  const duration = media.buffer.duration;
  return ((context.currentTime - anchor) % duration + duration) % duration;
}

function showTime() {
  if (!node) return;
  const p = media.info.plan;
  const now = currentPosition() / media.buffer.duration * p.sample_count;
  render(frameAt(p.boundaries, now));
  animation = requestAnimationFrame(showTime);
}

function stop() {
  if (!node) return;
  position = currentPosition();
  node.stop();
  node.disconnect();
  node = null;
  cancelAnimationFrame(animation);
  button.textContent = '播放';
}

function start() {
  node = context.createBufferSource();
  node.buffer = media.buffer;
  node.loop = true;
  node.connect(context.destination);
  anchor = context.currentTime - position;
  node.start(0, position);
  button.textContent = '暂停';
  showTime();
}

export function prepareAudio() {
  const AudioClock = window.AudioContext || window.webkitAudioContext;
  if (!AudioClock) throw Error('浏览器不支持音频时钟');
  context ??= new AudioClock();
  return context.resume();
}

export function resetPlayer() {
  generation++;
  stop();
  media = null;
  position = 0;
  paint.clearRect(0, 0, canvas.width, canvas.height);
  empty.hidden = false;
  blend.hidden = true;
  seek.disabled = button.disabled = true;
  label.textContent = '—';
  summary.textContent = '等待生成';
}

export async function loadPlayer(path, info, choice) {
  const active = ++generation;
  const query = new URLSearchParams(choice);
  const sound = request(`${path}/preview/audio?${query}`).then(response => response.arrayBuffer());
  const pages = [];
  // 每次加载少量拼页，保留其他工位操作的并发空间。
  const pictures = (async () => {
    for (let first = 0; first < info.atlas.sheets; first += 3) {
      if (active !== generation) return;
      const tasks = Array.from({length: Math.min(3, info.atlas.sheets - first)}, (_, offset) =>
        loadImage(`${path}/preview/sheet/${first + offset}?${query}`));
      pages.push(...await Promise.all(tasks));
    }
  })();
  const [audio] = await Promise.all([sound, pictures]);
  if (active !== generation) return;
  const buffer = await context.decodeAudioData(audio);
  if (active !== generation) return;
  media = {buffer, pages, info};
  position = 0;
  canvas.width = info.atlas.tile_width;
  canvas.height = info.atlas.tile_height;
  empty.hidden = true;
  seek.max = info.plan.frame_count - 1;
  seek.disabled = button.disabled = false;
  summary.textContent = `每圈 ${info.plan.frame_count} 格 · ${(info.plan.sample_count / info.sample_rate).toFixed(3)} 秒`;
  render(0);
}

export function playerEvents(report) {
  button.addEventListener('click', async () => {
    if (node) {
      stop();
      return;
    }
    const active = generation;
    try {
      await prepareAudio();
      if (active === generation && media && !node) start();
    } catch (error) {
      report(error.message, true);
    }
  });
  seek.addEventListener('input', () => {
    if (!media) return;
    const running = Boolean(node);
    stop();
    const index = Number(seek.value);
    position = media.info.plan.boundaries[index] / media.info.plan.sample_count * media.buffer.duration;
    render(index);
    if (running) start();
  });
}
