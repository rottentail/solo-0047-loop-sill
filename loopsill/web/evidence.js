import {capturePath} from './api.js';

const body = document.querySelector('#metrics');
const candidates = document.querySelector('#candidates');

export function percent(value) {
  return value === undefined ? '—' : `${(value * 100).toFixed(2)}%`;
}

export function showMetrics(before, after) {
  body.replaceChildren();
  if (!before) return;
  function row(label, start, end) {
    const tr = body.insertRow();
    for (const item of [label, percent(start), percent(end)]) tr.insertCell().textContent = item;
  }
  row('亮度差', before.luma, after?.luma);
  before.channels.forEach((channel, index) => {
    const name = before.channels.length === 1 ? '单声道' : ['左声道', '右声道'][index];
    row(`${name}边界跳变`, channel.jump, after?.channels[index]?.jump);
    row(`${name}窗口差`, channel.window_rms, after?.channels[index]?.window_rms);
  });
}

export function showSourceFrames(id, choice, maxFrame) {
  for (const [where, value, label] of [['head', choice?.start, '首格'], ['tail', choice?.end - 1, '末格']]) {
    const image = document.querySelector(`#${where}-image`);
    const caption = document.querySelector(`#${where}-caption`);
    const valid = id && Number.isInteger(value) && value >= 0 && value < maxFrame;
    caption.textContent = valid ? `${label} · ${value}` : label;
    if (!valid) {
      image.hidden = true;
      image.removeAttribute('src');
      continue;
    }
    const path = `${capturePath(id)}/frame/${value}`;
    if (image.getAttribute('src') === path) continue;
    image.hidden = true;
    image.onload = () => { image.hidden = false; };
    image.onerror = () => { image.hidden = true; };
    image.src = path;
  }
}

export function showCandidates(result, apply) {
  candidates.replaceChildren();
  document.querySelector('#scan-note').textContent = result ? `${result.eligible} 组可用 · ${result.omitted} 组越界` : '';
  result?.rows.forEach(item => {
    const row = candidates.insertRow();
    const {start, end} = item.selection;
    for (const data of [`[${start}, ${end})`, item.delta > 0 ? `+${item.delta}` : item.delta, percent(item.evidence.luma), percent(item.cost)]) {
      row.insertCell().textContent = data;
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '采用';
    button.addEventListener('click', () => apply(item.selection));
    row.insertCell().append(button);
  });
}
