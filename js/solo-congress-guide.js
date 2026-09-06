const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const progress = document.querySelector(".reading-progress");

function updateProgress() {
  if (!progress) return;
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = scrollable > 0 ? Math.min(window.scrollY / scrollable, 1) : 0;
  progress.style.transform = `scaleX(${ratio})`;
}

window.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();

if (!reduceMotion && window.gsap && window.ScrollTrigger) {
  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);

  // The h1 is this page's LCP element: it must stay visible from first paint
  // (transform-only intro), or the fade-from-0 pushes LCP past the animation.
  gsap.from(".hero-copy > h1", {
    y: 34,
    duration: 1.15,
    ease: "power3.out"
  });
  gsap.from(".hero-copy > p", {
    y: 34,
    opacity: 0,
    duration: 1.15,
    stagger: 0.11,
    ease: "power3.out"
  });

  gsap.from(".hero-footer", {
    y: 24,
    opacity: 0,
    duration: 1,
    delay: .45,
    ease: "power3.out"
  });

  gsap.utils.toArray(".reveal").forEach((element) => {
    gsap.from(element, {
      y: 48,
      opacity: 0,
      duration: .85,
      ease: "power2.out",
      scrollTrigger: {
        trigger: element,
        start: "top 86%",
        once: true
      }
    });
  });

  gsap.utils.toArray(".story-card").forEach((card, index) => {
    gsap.from(card, {
      y: index % 2 ? 56 : 30,
      opacity: 0,
      duration: .9,
      ease: "power3.out",
      scrollTrigger: {
        trigger: card,
        start: "top 88%",
        once: true
      }
    });
  });

  gsap.from(".quote-band blockquote", {
    y: 70,
    opacity: 0,
    duration: 1.1,
    ease: "power3.out",
    scrollTrigger: {
      trigger: ".quote-band",
      start: "top 72%",
      once: true
    }
  });
}

// Preserve the constellation with Canvas 2D: no WebGL startup or 3D downloads.
const canvas = document.querySelector("#connection-canvas");
if (canvas) {
  const context = canvas.getContext("2d");
  if (context) {
    const points = Array.from({ length: innerWidth < 700 ? 54 : 84 }, (_, i) => {
      const angle = i * 2.399963;
      const radius = 1.2 + Math.sqrt(i / (innerWidth < 700 ? 54 : 84)) * 4.9;
      return { x: Math.cos(angle) * radius + 1.55, y: Math.sin(angle) * radius * .72,
        z: Math.sin(i * 1.73) * 1.35 - .4,
        color: i % 11 === 0 ? "#ec4899" : i % 7 === 0 ? "#8b5cf6" : "#f8fafc" };
    });
    const edges = [];
    for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length && edges.length < 118; j++) {
      const a = points[i], b = points[j];
      if (Math.hypot(a.x-b.x, a.y-b.y, a.z-b.z) < 1.28) edges.push([i,j]);
    }
    let width, height, raf, last = 0, visible = true;
    const pointer = { x: 0, y: 0 }, target = { x: 0, y: 0 };
    function project(point, angle) {
      const x = point.x * Math.cos(angle) + point.z * Math.sin(angle);
      const z = -point.x * Math.sin(angle) + point.z * Math.cos(angle);
      const tilt = -.05 + pointer.y;
      const y = point.y * Math.cos(tilt) - z * Math.sin(tilt);
      const depth = 8.4 - (point.y * Math.sin(tilt) + z * Math.cos(tilt));
      const scale = height / (2 * Math.tan(23 * Math.PI / 180) * depth);
      return { x: width / 2 + x * scale, y: height / 2 - y * scale, scale };
    }
    function draw(time = 0) {
      context.clearRect(0, 0, width, height);
      pointer.x += (target.x - pointer.x) * .07;
      pointer.y += (target.y - pointer.y) * .07;
      const angle = time * .000035 + pointer.x;
      const projected = points.map(point => project(point, angle));
      context.globalAlpha = .13;
      context.strokeStyle = "#8b5cf6";
      context.lineWidth = 1;
      context.beginPath();
      for (const [i,j] of edges) {
        context.moveTo(projected[i].x, projected[i].y);
        context.lineTo(projected[j].x, projected[j].y);
      }
      context.stroke();
      context.strokeStyle = "#ec4899";
      context.beginPath();
      for (let i = 0; i <= 120; i++) {
        const a = i / 120 * Math.PI * 2 + time * .00009;
        const x = Math.cos(a) * 2.15, y = Math.sin(a) * 2.15;
        const point = project({ x: x * Math.cos(-.35) + y * Math.sin(.72) * Math.sin(-.35) + 1.65,
          y: y * Math.cos(.72) - .2, z: -x * Math.sin(-.35) + y * Math.sin(.72) * Math.cos(-.35) - .8 }, angle);
        if (i === 0) context.moveTo(point.x, point.y); else context.lineTo(point.x, point.y);
      }
      context.stroke();
      context.globalAlpha = .9;
      points.forEach((point,i) => {
        context.fillStyle = point.color;
        context.beginPath();
        context.arc(projected[i].x, projected[i].y, Math.max(.7, projected[i].scale * .025), 0, Math.PI * 2);
        context.fill();
      });
    }
    function frame(time) {
      if (time - last >= 1000 / 30) { draw(time); last = time; }
      raf = requestAnimationFrame(frame);
    }
    function updateAnimation() {
      cancelAnimationFrame(raf);
      if (!reduceMotion && visible && !document.hidden) raf = requestAnimationFrame(frame);
    }
    function resize() {
      width = canvas.clientWidth; height = canvas.clientHeight;
      const ratio = Math.min(devicePixelRatio, 1.75);
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      draw(last);
    }
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", event => {
      target.x = (event.clientX / innerWidth - .5) * .22;
      target.y = (event.clientY / innerHeight - .5) * .16;
    }, { passive: true });
    document.addEventListener("visibilitychange", updateAnimation);
    new IntersectionObserver(entries => { visible = entries[0].isIntersecting; updateAnimation(); }).observe(canvas);
    resize();
    updateAnimation();
  }
}
