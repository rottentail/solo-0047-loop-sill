export async function request(path, body, options = {}) {
  const settings = body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
  };
  const response = await fetch(path, {...settings, ...options});
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw Error(error.error || `请求失败（${response.status}）`);
  }
  return response;
}

export async function json(path, body, options) {
  return (await request(path, body, options)).json();
}

export function capturePath(id) {
  return `/api/captures/${id}`;
}

export async function upload(form) {
  const data = new FormData(form);
  const video = data.get('video');
  const audio = data.get('audio');
  if (video.size > 28 * 1024 * 1024 || audio.size > 5 * 1024 * 1024) {
    throw Error('画面或拾音超过登记上限');
  }
  const prefix = new DataView(new ArrayBuffer(4));
  prefix.setUint32(0, video.size);
  return json(`/api/captures?label=${encodeURIComponent(data.get('label'))}`, undefined, {
    method: 'POST', headers: {'Content-Type': 'application/octet-stream'},
    body: new Blob([prefix.buffer, video, audio]),
  });
}

export function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(Error('画格预演页无法加载'));
    image.src = url;
  });
}
