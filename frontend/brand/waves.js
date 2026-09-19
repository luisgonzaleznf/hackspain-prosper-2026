// The two background fields behind the page.
//
// Both shaders come from React Bits (MIT + Commons Clause, (c) David Haz):
// Gradient Waves and Grainient, https://reactbits.dev/backgrounds. They are
// recoloured to the ROSARIO palette and ported off React and ogl to plain WebGL2.
//
// Grainient drifts continuously, at Marcos's request. The wave field behind the hero
// is a raymarch and far more expensive per pixel, so it is drawn once and left still.
// The loop stops whenever the tab is hidden, both fields render at half resolution,
// and under prefers-reduced-motion nothing moves at all.
(() => {
  const VERT = `#version 300 es
in vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;
  const WAVES_FRAG = `#version 300 es
precision highp float;
uniform vec2 iResolution;
uniform float iTime;
uniform float uSpeed;
uniform float uAmplitude;
uniform float uWaveScale;
uniform float uWaveRatio;
uniform float uSwell;
uniform float uTurbulence;
uniform float uTilt;
uniform float uZoom;
uniform float uHeight;
uniform float uFogDepth;
uniform float uSteps;
uniform float uBrightness;
uniform float uOpacity;
uniform float uGrain;
uniform float uGrainIntensity;
uniform vec2 uMouse;
uniform float uParallax;
uniform bool uEnableMouse;
uniform vec3 uHorizonColor;
uniform vec3 uWaveColor;
uniform vec3 uCrestColor;
out vec4 fragColor;

const float MAX_DIST = 20000.0;

float hash21(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

float plasma(vec3 r, vec2 freq, vec4 tc) {
  float mx = r.x + tc.x;
  mx += uSwell * sin((r.y + mx) / 20.0 + tc.y);
  float my = r.y - tc.z;
  my += uTurbulence * cos(r.x / 23.0 + tc.w);
  return r.z - (sin(mx * freq.x) * uAmplitude + sin(my * freq.y) * uAmplitude + uHeight);
}

float raymarch(vec3 pos, vec3 dir, vec2 freq, vec4 tc) {
  float dist = 0.0;
  for (int i = 0; i < 128; i++) {
    if (float(i) >= uSteps) break;
    float dscene = plasma(pos + dist * dir, freq, tc);
    if (abs(dscene) < 0.1) break;
    dist += 0.9 * dscene;
    if (!(abs(dist) < MAX_DIST)) return MAX_DIST;
  }
  return dist;
}

void main() {
  float T = iTime * uSpeed;
  vec2 freq = vec2(uWaveScale / 7.0, (uWaveScale * uWaveRatio) / 3.0);
  vec4 tc = vec4(T / 0.130, T / 0.810, T / 0.200, T / 0.710);
  float c, s;
  float vfov = (3.14159 / 2.3) / max(uZoom, 0.05);
  vec3 cam = vec3(0.0, 0.0, 30.0);
  vec2 uv = (gl_FragCoord.xy / iResolution.xy) - 0.5;
  uv.x *= iResolution.x / iResolution.y;
  uv.y *= -1.0;

  vec3 dir = vec3(0.0, 0.0, -1.0);
  float ulen = length(uv);
  float xrot = vfov * ulen;
  c = cos(xrot); s = sin(xrot);
  dir = mat3(1.0, 0.0, 0.0, 0.0, c, -s, 0.0, s, c) * dir;
  vec2 nuv = ulen > 1e-5 ? uv / ulen : vec2(1.0, 0.0);
  c = nuv.x; s = nuv.y;
  dir = mat3(c, -s, 0.0, s, c, 0.0, 0.0, 0.0, 1.0) * dir;
  c = cos(uTilt); s = sin(uTilt);
  dir = mat3(c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c) * dir;

  if (uEnableMouse) {
    float yaw = (uMouse.x - 0.5) * uParallax * 0.4;
    float pitch = (uMouse.y - 0.5) * uParallax * 0.4;
    c = cos(yaw); s = sin(yaw);
    dir = mat3(c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c) * dir;
    c = cos(pitch); s = sin(pitch);
    dir = mat3(1.0, 0.0, 0.0, 0.0, c, -s, 0.0, s, c) * dir;
  }

  float dist = raymarch(cam, dir, freq, tc);
  vec3 pos = cam + dist * dir;

  float t = clamp(uFogDepth / max(dist, 0.001), 0.0, 1.0);
  vec3 body = mix(uWaveColor, uCrestColor, clamp(pos.z * 0.08 + 0.5, 0.0, 1.0));
  vec3 col = mix(uHorizonColor, body, t);
  col *= uBrightness;
  col = clamp(col, 0.0, 1.0);

  float alpha = clamp(t, 0.0, 1.0) * uOpacity;
  if (uGrain > 0.5) {
    float g = hash21(gl_FragCoord.xy + mod(iTime, 64.0) * 11.0);
    alpha += (g - 0.5) * uGrainIntensity;
  }
  alpha = clamp(alpha, 0.0, 1.0);
  fragColor = vec4(col * alpha, alpha);
}`;
  const GRAIN_FRAG = `#version 300 es
precision highp float;
uniform vec2 iResolution;
uniform float iTime;
uniform float uTimeSpeed;
uniform float uColorBalance;
uniform float uWarpStrength;
uniform float uWarpFrequency;
uniform float uWarpSpeed;
uniform float uWarpAmplitude;
uniform float uBlendAngle;
uniform float uBlendSoftness;
uniform float uRotationAmount;
uniform float uNoiseScale;
uniform float uGrainAmount;
uniform float uGrainScale;
uniform float uGrainAnimated;
uniform float uContrast;
uniform float uGamma;
uniform float uSaturation;
uniform vec2 uCenterOffset;
uniform float uZoom;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform vec3 uColor3;
uniform float uLightMode;
out vec4 fragColor;
#define S(a,b,t) smoothstep(a,b,t)
mat2 Rot(float a){float s=sin(a),c=cos(a);return mat2(c,-s,s,c);} 
vec2 hash(vec2 p){p=vec2(dot(p,vec2(2127.1,81.17)),dot(p,vec2(1269.5,283.37)));return fract(sin(p)*43758.5453);} 
float noise(vec2 p){vec2 i=floor(p),f=fract(p),u=f*f*(3.0-2.0*f);float n=mix(mix(dot(-1.0+2.0*hash(i+vec2(0.0,0.0)),f-vec2(0.0,0.0)),dot(-1.0+2.0*hash(i+vec2(1.0,0.0)),f-vec2(1.0,0.0)),u.x),mix(dot(-1.0+2.0*hash(i+vec2(0.0,1.0)),f-vec2(0.0,1.0)),dot(-1.0+2.0*hash(i+vec2(1.0,1.0)),f-vec2(1.0,1.0)),u.x),u.y);return 0.5+0.5*n;}
void mainImage(out vec4 o, vec2 C){
  float t=iTime*uTimeSpeed;
  vec2 uv=C/iResolution.xy;
  float ratio=iResolution.x/iResolution.y;
  vec2 tuv=uv-0.5+uCenterOffset;
  tuv/=max(uZoom,0.001);

  float degree=noise(vec2(t*0.1,tuv.x*tuv.y)*uNoiseScale);
  tuv.y*=1.0/ratio;
  tuv*=Rot(radians((degree-0.5)*uRotationAmount+180.0));
  tuv.y*=ratio;

  float frequency=uWarpFrequency;
  float ws=max(uWarpStrength,0.001);
  float amplitude=uWarpAmplitude/ws;
  float warpTime=t*uWarpSpeed;
  tuv.x+=sin(tuv.y*frequency+warpTime)/amplitude;
  tuv.y+=sin(tuv.x*(frequency*1.5)+warpTime)/(amplitude*0.5);

  vec3 colLav=uColor1;
  vec3 colOrg=uColor2;
  vec3 colDark=uColor3;
  float b=uColorBalance;
  float s=max(uBlendSoftness,0.0);
  mat2 blendRot=Rot(radians(uBlendAngle));
  float blendX=(tuv*blendRot).x;
  float edge0=-0.3-b-s;
  float edge1=0.2-b+s;
  float v0=0.5-b+s;
  float v1=-0.3-b-s;
  vec3 layer1=mix(colDark,colOrg,S(edge0,edge1,blendX));
  vec3 layer2=mix(colOrg,colLav,S(edge0,edge1,blendX));
  vec3 col=mix(layer1,layer2,S(v0,v1,tuv.y));

  vec2 grainUv=uv*max(uGrainScale,0.001);
  if(uGrainAnimated>0.5){grainUv+=vec2(iTime*0.05);} 
  float grain=fract(sin(dot(grainUv,vec2(12.9898,78.233)))*43758.5453);
  col+=(grain-0.5)*uGrainAmount;

  col=(col-0.5)*uContrast+0.5;
  float luma=dot(col,vec3(0.2126,0.7152,0.0722));
  col=mix(vec3(luma),col,uSaturation);
  col=pow(max(col,0.0),vec3(1.0/max(uGamma,0.001)));
  col=clamp(col,0.0,1.0);
  if(uLightMode>0.5){
    float energy=max(max(col.r,col.g),col.b);
    vec3 hue=col/max(energy,0.001);
    float chroma=length(col-vec3(dot(col,vec3(0.333333))));
    float coverage=clamp(0.12+chroma*1.15+energy*0.18,0.0,0.88);
    col=mix(vec3(1.0),clamp(hue*0.58+col*0.18,0.0,1.0),coverage);
  }

  o=vec4(col,1.0);
}
void main(){
  vec4 o=vec4(0.0);
  mainImage(o,gl_FragCoord.xy);
  fragColor=o;
}`;

  const styles = getComputedStyle(document.documentElement);
  const rgb = (name) => {
    const hex = styles.getPropertyValue(name).trim();
    if (!/^#[0-9a-f]{6}$/i.test(hex)) return null;
    return [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
  };

  // One field: compiles its shader, draws on demand, and never runs a clock.
  const field = (id, frag, setup, scale) => {
    const canvas = document.getElementById(id);
    if (!canvas) return null;
    const gl = canvas.getContext("webgl2", { alpha: true, antialias: false, premultipliedAlpha: true });
    if (!gl) return null; // No WebGL2: the crimson page colour stands on its own.

    const compile = (type, source) => {
      const sh = gl.createShader(type);
      gl.shaderSource(sh, source);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) { gl.deleteShader(sh); return null; }
      return sh;
    };
    const vs = compile(gl.VERTEX_SHADER, VERT), fs = compile(gl.FRAGMENT_SHADER, frag);
    if (!vs || !fs) return null;
    const program = gl.createProgram();
    gl.attachShader(program, vs); gl.attachShader(program, fs); gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
    gl.useProgram(program);

    // One full-screen triangle.
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(program, "position");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const u = (name) => gl.getUniformLocation(program, name);
    if (setup(gl, u) === false) return null;
    const uTime = u("iTime"), uRes = u("iResolution");

    // Half resolution, capped: these are out-of-focus backgrounds and the cost is per pixel.
    let w = 0, h = 0, queued = false, time = 0, quality = 1;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5) * 0.5 * quality;
      w = Math.max(1, Math.round(canvas.clientWidth * dpr));
      h = Math.max(1, Math.round(canvas.clientHeight * dpr));
      canvas.width = w; canvas.height = h;
      gl.viewport(0, 0, w, h);
      gl.uniform2f(uRes, w, h);
    };
    const draw = () => {
      queued = false;
      gl.uniform1f(uTime, time);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    const request = () => { if (!queued) { queued = true; requestAnimationFrame(draw); } };

    resize();
    draw();
    canvas.classList.add("ready");
    return {
      resize, request,
      drawAt: (seconds) => { time = seconds * scale; draw(); },
      // Called when the clock finds the machine cannot keep up.
      relax: (q) => { quality = q; resize(); },
    };
  };

  const horizon = rgb("--color-inkline-crimson"), maroon = rgb("--color-dusk-maroon");
  const fire = rgb("--color-nava-fire"), ember = rgb("--color-ember-glow");
  const surface = rgb("--color-obsidian-burgundy");
  if (!horizon || !maroon || !fire || !ember || !surface) return;

  // Gradient waves: the crimson canvas at the horizon, fire in the troughs, one
  // ember crest. Brightness and opacity stay low so body copy keeps its contrast.
  const waves = field("waves", WAVES_FRAG, (gl, u) => {
    gl.uniform3fv(u("uHorizonColor"), horizon);
    gl.uniform3fv(u("uWaveColor"), fire);
    gl.uniform3fv(u("uCrestColor"), ember);
    gl.uniform1f(u("uSpeed"), 0.4);
    gl.uniform1f(u("uAmplitude"), 3.2);
    gl.uniform1f(u("uWaveScale"), 0.6);
    gl.uniform1f(u("uWaveRatio"), 0.9);
    gl.uniform1f(u("uSwell"), 35);
    gl.uniform1f(u("uTurbulence"), 20);
    gl.uniform1f(u("uTilt"), 1.11);
    gl.uniform1f(u("uZoom"), 1);
    gl.uniform1f(u("uHeight"), 5.5);
    gl.uniform1f(u("uFogDepth"), 34);
    gl.uniform1f(u("uSteps"), 64);
    gl.uniform1f(u("uBrightness"), 0.8);
    gl.uniform1f(u("uOpacity"), 0.5);
    gl.uniform1f(u("uGrain"), 1);
    gl.uniform1f(u("uGrainIntensity"), 0.012);
    gl.uniform1f(u("uParallax"), 0);
    gl.uniform1i(u("uEnableMouse"), 0);
    gl.uniform2f(u("uMouse"), 0.5, 0.5);
  }, 0.045);

  // Grainient: the slow field under the rest of the page. Maroon and fire over the
  // crimson canvas, low contrast and heavy grain, so it reads as depth, not pattern.
  const grain = field("grainient", GRAIN_FRAG, (gl, u) => {
    gl.uniform3fv(u("uColor1"), maroon);
    gl.uniform3fv(u("uColor2"), horizon);
    gl.uniform3fv(u("uColor3"), surface);
    gl.uniform1f(u("uTimeSpeed"), 0.25);
    gl.uniform1f(u("uColorBalance"), 0);
    gl.uniform1f(u("uWarpStrength"), 1);
    gl.uniform1f(u("uWarpFrequency"), 5);
    gl.uniform1f(u("uWarpSpeed"), 2);
    gl.uniform1f(u("uWarpAmplitude"), 50);
    gl.uniform1f(u("uBlendAngle"), 0);
    gl.uniform1f(u("uBlendSoftness"), 0.05);
    gl.uniform1f(u("uRotationAmount"), 500);
    gl.uniform1f(u("uNoiseScale"), 2);
    gl.uniform1f(u("uGrainAmount"), 0.02);
    gl.uniform1f(u("uGrainScale"), 2);
    gl.uniform1f(u("uGrainAnimated"), 0);
    gl.uniform1f(u("uContrast"), 0.95);
    gl.uniform1f(u("uGamma"), 1);
    gl.uniform1f(u("uSaturation"), 0.8);
    gl.uniform2f(u("uCenterOffset"), 0, 0);
    gl.uniform1f(u("uZoom"), 0.9);
    gl.uniform1f(u("uLightMode"), 0);
  }, 0.11);

  const fields = [waves, grain].filter(Boolean);
  if (!fields.length) return;
  for (const f of fields) f.drawAt(0);

  addEventListener("resize", () => { for (const f of fields) { f.resize(); f.request(); } });

  const still = matchMedia("(prefers-reduced-motion: reduce)");
  // Only the cheap field is on the clock.
  const animated = grain ? [grain] : [];
  let raf = 0, elapsed = 0, last = 0, painted = 0, cost = 0, relaxed = false;
  const FRAME_MS = 1000 / 30; // 30fps is plenty for a slow drift and halves the cost
  const frame = (now) => {
    raf = requestAnimationFrame(frame);
    const dt = now - last;
    if (dt < FRAME_MS) return;
    // Advance by real elapsed time, clamped so a backgrounded tab cannot jump the
    // field forward by minutes when it comes back.
    elapsed += Math.min(dt / 1000, 0.1);
    last = now;
    const t0 = performance.now();
    for (const f of animated) f.drawAt(elapsed);
    // Rolling cost of a painted frame; a machine that cannot hold 30fps gets a
    // smaller buffer once, and then the field stops moving rather than stuttering.
    cost += (performance.now() - t0 - cost) * 0.1;
    if (++painted > 30 && cost > 18) {
      if (relaxed) { animated.length = 0; stop(); return; }
      relaxed = true; grain.relax(0.7); painted = 0; cost = 0;
    }
  };
  const start = () => { if (!raf && animated.length && !still.matches && !document.hidden) { last = performance.now(); raf = requestAnimationFrame(frame); } };
  const stop = () => { if (raf) { cancelAnimationFrame(raf); raf = 0; } };
  // Nothing runs while the tab is in the background, or when the reader asks for stillness.
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
  still.addEventListener("change", () => (still.matches ? stop() : start()));
  start();
})();
