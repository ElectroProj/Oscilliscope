(() => {
  // Canvas and context
  const canvas = document.getElementById("waveform");
  const ctx = canvas.getContext("2d");
  // Controls
  const runStopBtn = document.getElementById("runStop");
  const triggerModeSel = document.getElementById("triggerMode");
  const triggerLevelInput = document.getElementById("triggerLevel");
  const voltsDivSel = document.getElementById("voltsDiv");
  const timeScaleSel = document.getElementById("timeScale");
  const statsDiv = document.getElementById("stats");

  let running = true;
  let triggerMode = triggerModeSel.value;
  let triggerLevel = parseInt(triggerLevelInput.value, 10);
  let voltsDiv = parseFloat(voltsDivSel.value);
  let timeScale = parseFloat(timeScaleSel.value);
  let lastFrameCounter = null;
  let droppedFrames = 0;
  let lastTimestamp = performance.now();
  let fps = 0;
  let triggeredOnce = false;

  function resizeCanvas() {
    // Match the canvas’s internal resolution to its CSS size
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
  }
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  runStopBtn.addEventListener("click", () => {
    running = !running;
    runStopBtn.textContent = running ? "Stop" : "Run";
    // When resuming after single trigger, reset flag
    if (running && triggerMode === "single") {
      triggeredOnce = false;
    }
  });

  triggerModeSel.addEventListener("change", () => {
    triggerMode = triggerModeSel.value;
    if (triggerMode === "single") {
      triggeredOnce = false;
    }
  });
  triggerLevelInput.addEventListener("input", () => {
    triggerLevel = parseInt(triggerLevelInput.value, 10);
  });
  voltsDivSel.addEventListener("change", () => {
    voltsDiv = parseFloat(voltsDivSel.value);
  });
  timeScaleSel.addEventListener("change", () => {
    timeScale = parseFloat(timeScaleSel.value);
  });

  function updateStats(frame) {
    statsDiv.textContent = `Frame ${frame.frame} | Samples ${frame.sample_count} | FPS ${fps.toFixed(
      1
    )} | Dropped ${droppedFrames}`;
  }

  function drawWave(samples) {
    const width = canvas.width;
    const height = canvas.height;
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    // Compute vertical scaling: each division is voltsDiv volts.  There are 8 vertical divisions.
    const countsPerVolt = 4095 / 3.3;
    const countsPerDiv = voltsDiv * countsPerVolt;
    const pixelsPerDiv = height / 8;
    const scaleY = pixelsPerDiv / countsPerDiv;
    // Horizontal scaling: timeScale multiplies the width per sample
    const step = width / (samples.length / timeScale);
    let x = 0;
    ctx.beginPath();
    for (let i = 0; i < samples.length; i++) {
      const s = samples[i];
      // Convert sample to deviation from mid‑scale (2048)
      const v = (s - 2048) * scaleY;
      const y = height / 2 - v;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      x += step;
    }
    ctx.strokeStyle = "#007acc";
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  function processFrame(frame) {
    // Compute dropped frames
    if (lastFrameCounter !== null && frame.frame > lastFrameCounter + 1) {
      droppedFrames += frame.frame - lastFrameCounter - 1;
    }
    lastFrameCounter = frame.frame;
    // Compute FPS
    const now = performance.now();
    fps = 1000 / (now - lastTimestamp);
    lastTimestamp = now;
    // Determine whether to render based on trigger mode
    let shouldRender = true;
    if (triggerMode === "normal" || triggerMode === "single") {
      // Find a threshold crossing: previous < level, current >= level
      shouldRender = false;
      const samples = frame.samples;
      for (let i = 1; i < samples.length; i++) {
        if (samples[i - 1] < triggerLevel && samples[i] >= triggerLevel) {
          shouldRender = true;
          break;
        }
      }
      if (triggerMode === "single") {
        if (shouldRender && !triggeredOnce) {
          triggeredOnce = true;
          // After single trigger fires once, stop running
          running = false;
          runStopBtn.textContent = "Run";
        } else {
          shouldRender = false;
        }
      }
    }
    if (shouldRender) {
      drawWave(frame.samples);
    }
    updateStats(frame);
  }

  // Connect WebSocket
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => {
    statsDiv.textContent = "Connected";
  };
  ws.onclose = () => {
    statsDiv.textContent = "Disconnected";
  };
  ws.onerror = () => {
    statsDiv.textContent = "WebSocket error";
  };
  ws.onmessage = (event) => {
    if (!running) {
      return;
    }
    try {
      const frame = JSON.parse(event.data);
      processFrame(frame);
    } catch (err) {
      console.error("Failed to parse frame", err);
    }
  };
})();