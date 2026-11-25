import {capturePath, json, upload} from './api.js';
import {showCandidates, showMetrics, showSourceFrames} from './evidence.js';
import {readHistory, showHistory} from './history.js';
import {loadPlayer, playerEvents, prepareAudio, resetPlayer} from './audition.js';
import {drawWave} from './wave.js';

const $ = selector => document.querySelector(selector);
const picker = $('#capture');
const form = $('#selection');
const editable = ['start', 'end', 'overlap', 'offset'];
const screen = {capture: null, revision: 0, latest: 0, version: 0, busy: false};

function notice(message, error = false) {
  $('#notice').textContent = message;
  $('#notice').dataset.error = String(error);
}

function controls() {
  const disabled = !screen.capture || screen.busy;
  $('#selection-controls').disabled = disabled;
  for (const action of ['measure', 'preview', 'save', 'scan-run']) $(`#${action}`).disabled = disabled;
  picker.disabled = screen.busy;
  document.querySelectorAll('[data-demo], #upload button').forEach(button => { button.disabled = screen.busy; });
}

async function run(action) {
  if (screen.busy) return;
  screen.busy = true;
  controls();
  try {
    await action();
  } catch (error) {
    notice(error.message, true);
  } finally {
    screen.busy = false;
    controls();
  }
}

function choice() {
  const values = Object.fromEntries(editable.map(key => [key, form.elements[key].valueAsNumber]));
  if (Object.values(values).some(value => !Number.isInteger(value))) throw Error('请填写完整的整数选区');
  return values;
}

function revisionLabel() {
  $('#active-revision').textContent = screen.revision ? `第 ${screen.revision} 稿` : '未保存';
}

function invalidate(raw) {
  screen.version++;
  resetPlayer();
  showMetrics(null);
  drawWave(null);
  showCandidates(null);
  showSourceFrames(screen.capture?.id, raw, screen.capture?.frame_count);
  revisionLabel();
}

function fill(raw, revision = 0) {
  for (const key of editable) form.elements[key].value = raw?.[key] ?? '';
  screen.revision = revision;
  invalidate(raw);
}

async function refreshHistory() {
  const id = screen.capture.id;
  const data = await readHistory(id);
  if (screen.capture?.id !== id) return [];
  screen.latest = data.drafts[0]?.revision || 0;
  showHistory(data, draft => {
    if (screen.busy) return;
    fill(draft.selection, draft.revision);
    notice(`已打开第 ${draft.revision} 稿`);
  }, revision => run(async () => {
    await json(`${capturePath(id)}/handoffs`, {revision});
    await refreshHistory();
    notice(`第 ${revision} 稿已封存，可下载环带`);
  }));
  return data.drafts;
}

async function selectCapture(item) {
  screen.capture = item;
  screen.latest = 0;
  picker.value = item?.id || '';
  showHistory(null);
  if (!item) {
    $('#facts').textContent = '选择演示或登记画面与拾音。';
    fill(null);
    return;
  }
  const channels = item.channels === 2 ? '双声道' : '单声道';
  const fps = item.fps[1] === 1 ? item.fps[0] : item.fps.join('/');
  $('#facts').textContent = `${item.width} × ${item.height} · ${fps} 格/秒 · ${item.frame_count} 格 · ${item.sample_rate} Hz ${channels}`;
  fill(item.suggested);
  const drafts = await refreshHistory();
  if (drafts.length) fill(drafts[0].selection, drafts[0].revision);
  notice(item.suggested || drafts.length ? `已载入「${item.label}」` : '默认偏移下没有四格完整拾音，请检查偏移和素材');
}

async function refreshPicker(selected) {
  const rows = await json('/api/captures');
  picker.replaceChildren(new Option('请选择素材', ''));
  for (const item of rows) picker.add(new Option(item.label, item.id));
  await selectCapture(rows.find(row => row.id === selected) || rows[0] || null);
}

async function measureSource(path, raw) {
  const version = screen.version;
  const [reading, waveform] = await Promise.all([
    json(`${path}/measure`, raw), json(`${path}/waveform`, {selection: raw, bins: 240}),
  ]);
  if (version === screen.version) {
    showMetrics(reading);
    drawWave(waveform);
  }
}

form.addEventListener('submit', event => event.preventDefault());
form.addEventListener('input', () => {
  screen.revision = 0;
  const frames = Object.fromEntries(editable.map(key => [key, form.elements[key].valueAsNumber]));
  invalidate(frames);
});
picker.addEventListener('change', () => run(async () => {
  const selected = picker.value;
  await selectCapture(selected ? await json(capturePath(selected)) : null);
}));
for (const button of document.querySelectorAll('[data-demo]')) {
  button.addEventListener('click', () => run(async () => {
    notice('正在生成声画素材…');
    const item = await json(`/api/demos/${button.dataset.demo}`, {});
    await refreshPicker(item.id);
  }));
}
$('#upload').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => {
    notice('正在读取两份媒体文件…');
    const item = await upload(event.target);
    event.target.reset();
    $('.intake').open = false;
    await refreshPicker(item.id);
  });
});
$('#measure').addEventListener('click', () => run(async () => {
  await measureSource(capturePath(screen.capture.id), choice());
  notice('已更新亮度与各声道接点读数');
}));
$('#preview').addEventListener('click', () => run(async () => {
  notice('正在编排一圈画格和拾音…');
  await prepareAudio();
  const raw = choice();
  const path = capturePath(screen.capture.id);
  const info = await json(`${path}/preview`, raw);
  await loadPlayer(path, info, raw);
  const waveform = await json(`${path}/waveform`, {selection: raw, bins: 240});
  drawWave(waveform);
  showMetrics(info.before, info.after);
  notice('预演就绪，可播放或拖动画格');
}));
$('#save').addEventListener('click', () => run(async () => {
  const path = capturePath(screen.capture.id);
  try {
    const saved = await json(`${path}/drafts`, {selection: choice(), expected: screen.latest});
    screen.revision = saved.revision;
    revisionLabel();
    notice(`已保存第 ${saved.revision} 稿`);
  } finally {
    await refreshHistory();
  }
}));
$('#scan').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => {
    const data = new FormData(event.target);
    const raw = choice();
    const path = capturePath(screen.capture.id);
    const result = await json(`${path}/scan`, {selection: raw, radius: Number(data.get('radius')), focus: data.get('focus')});
    showCandidates(result, selection => run(async () => {
      fill(selection);
      await measureSource(path, selection);
      notice('已采用候选区间');
    }));
    notice('已按接点差异排列等长候选');
  });
});
playerEvents(notice);
run(refreshPicker);
