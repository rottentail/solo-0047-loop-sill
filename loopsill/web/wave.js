const canvas = document.querySelector('#wave');
const ctx = canvas.getContext('2d');
const colors = ['#80cebc', '#eead77'];

export function drawWave(reading) {
  const {width, height} = canvas;
  ctx.clearRect(0, 0, width, height);
  document.querySelector('#wave-span').textContent = reading ? `[${reading.first_sample}, ${reading.end_sample}) 样本` : '';
  if (!reading) return;
  const band = height / reading.peaks.length;
  reading.peaks.forEach((bins, channel) => {
    const middle = (channel + .5) * band;
    ctx.strokeStyle = '#3b5660';
    ctx.beginPath();
    ctx.moveTo(0, middle);
    ctx.lineTo(width, middle);
    ctx.stroke();
    ctx.strokeStyle = colors[channel];
    ctx.beginPath();
    bins.forEach(([low, high], index) => {
      const x = (index + .5) * width / bins.length;
      ctx.moveTo(x, middle - high / 32768 * band * .44);
      ctx.lineTo(x, middle - low / 32768 * band * .44 + 1);
    });
    ctx.stroke();
  });
}
