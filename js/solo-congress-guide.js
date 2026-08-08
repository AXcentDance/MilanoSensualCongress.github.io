import * as THREE from "/vendor/three/three.module.min.js";

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

  gsap.from(".hero-copy > *", {
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

const canvas = document.querySelector("#connection-canvas");

if (canvas && !reduceMotion) {
  try {
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(46, 1, .1, 100);
    const group = new THREE.Group();
    const pointCount = window.innerWidth < 700 ? 54 : 84;
    const positions = new Float32Array(pointCount * 3);
    const colors = new Float32Array(pointCount * 3);
    const pink = new THREE.Color(0xec4899);
    const purple = new THREE.Color(0x8b5cf6);
    const white = new THREE.Color(0xf8fafc);
    const points = [];

    camera.position.z = 8.4;
    scene.add(group);

    for (let i = 0; i < pointCount; i += 1) {
      const angle = i * 2.399963;
      const radius = 1.2 + Math.sqrt(i / pointCount) * 4.9;
      const x = Math.cos(angle) * radius + 1.55;
      const y = Math.sin(angle) * radius * .72;
      const z = (Math.sin(i * 1.73) * 1.35) - .4;
      const point = new THREE.Vector3(x, y, z);
      const color = i % 11 === 0 ? pink : (i % 7 === 0 ? purple : white);

      points.push(point);
      positions.set([x, y, z], i * 3);
      colors.set([color.r, color.g, color.b], i * 3);
    }

    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    pointGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const pointMaterial = new THREE.PointsMaterial({
      size: .075,
      transparent: true,
      opacity: .9,
      vertexColors: true,
      sizeAttenuation: true
    });
    group.add(new THREE.Points(pointGeometry, pointMaterial));

    const lineCoordinates = [];
    let lineCount = 0;
    for (let i = 0; i < points.length && lineCount < 118; i += 1) {
      for (let j = i + 1; j < points.length && lineCount < 118; j += 1) {
        if (points[i].distanceTo(points[j]) < 1.28) {
          lineCoordinates.push(
            points[i].x, points[i].y, points[i].z,
            points[j].x, points[j].y, points[j].z
          );
          lineCount += 1;
        }
      }
    }

    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(lineCoordinates, 3));
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x8b5cf6,
      transparent: true,
      opacity: .13
    });
    group.add(new THREE.LineSegments(lineGeometry, lineMaterial));

    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0xec4899,
      wireframe: true,
      transparent: true,
      opacity: .13
    });
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.15, .018, 6, 120), ringMaterial);
    ring.position.set(1.65, -.2, -.8);
    ring.rotation.x = .72;
    ring.rotation.y = -.35;
    group.add(ring);

    const pointer = { x: 0, y: 0 };
    const target = { x: 0, y: 0 };
    let rafId;

    function resize() {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    }

    function onPointerMove(event) {
      target.x = (event.clientX / window.innerWidth - .5) * .22;
      target.y = (event.clientY / window.innerHeight - .5) * .16;
    }

    function render(time = 0) {
      pointer.x += (target.x - pointer.x) * .035;
      pointer.y += (target.y - pointer.y) * .035;
      group.rotation.y = time * .000035 + pointer.x;
      group.rotation.x = -.05 + pointer.y;
      ring.rotation.z = time * .00009;
      renderer.render(scene, camera);
      rafId = requestAnimationFrame(render);
    }

    function onVisibilityChange() {
      if (document.hidden) {
        cancelAnimationFrame(rafId);
      } else {
        rafId = requestAnimationFrame(render);
      }
    }

    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange);
    resize();
    render();
  } catch (error) {
    canvas.hidden = true;
  }
}
