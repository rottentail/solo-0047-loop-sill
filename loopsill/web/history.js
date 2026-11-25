import {capturePath, json} from './api.js';

const list = document.querySelector('#history');
const empty = document.querySelector('#history-empty');

export async function readHistory(id) {
  const path = capturePath(id);
  const [drafts, handoffs] = await Promise.all([json(`${path}/drafts`), json(`${path}/handoffs`)]);
  return {drafts, handoffs};
}

export function showHistory(data, open, freeze) {
  list.replaceChildren();
  empty.hidden = Boolean(data?.drafts.length);
  if (!data) return;
  const frozen = new Map(data.handoffs.map(item => [item.revision, item]));
  for (const draft of data.drafts) {
    const item = document.createElement('li');
    const description = document.createElement('span');
    const {start, end, overlap} = draft.selection;
    description.textContent = `第 ${draft.revision} 稿 · [${start}, ${end}) · 叠 ${overlap} 格`;
    const actions = document.createElement('div');
    actions.className = 'button-row';
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '打开';
    button.addEventListener('click', () => open(draft));
    actions.append(button);
    if (frozen.has(draft.revision)) {
      const link = document.createElement('a');
      link.href = `/api/handoffs/${frozen.get(draft.revision).id}`;
      link.textContent = '下载环带';
      actions.append(link);
    } else {
      const seal = document.createElement('button');
      seal.type = 'button';
      seal.textContent = '封存';
      seal.addEventListener('click', () => freeze(draft.revision));
      actions.append(seal);
    }
    item.append(description, actions);
    list.append(item);
  }
}
