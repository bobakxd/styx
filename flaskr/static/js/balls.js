// Some random colors
const colors = ["#3CC157", "#2AA7FF", "#1B1B1B", "#FCBC0F", "#F85F36"];

const numBalls = 50;
const balls = [];

var element = document.getElementsByClassName('background-wrapper')[0];

for (let i = 0; i < numBalls; i++) {
  let ball = document.createElement("div");
  ball.classList.add("ball");
  ball.style.background = colors[Math.floor(Math.random() * colors.length)];
  ball.style.left = `${Math.floor(Math.random() * element.offsetWidth)}px`;
  ball.style.top = `${Math.floor(Math.random() * element.offsetHeight)}px`;
  ball.style.transform = `scale(${Math.random()})`;
  var widthEm = Math.random();
  ball.style.width = `${widthEm}em`;
  ball.style.height = ball.style.width;
  //var emSize = parseFloat(getComputedStyle(element).fontSize);
  //ball.style.borderWidth = `${.2 * widthEm * emSize}px`;
  
  balls.push(ball);
  //document.body.append(ball);
  element.append(ball);
}

// Keyframes
balls.forEach((el, i, ra) => {
  let to = {
    x: Math.random() * (i % 2 === 0 ? -11 : 11),
    y: Math.random() * 12
  };

  let anim = el.animate(
    [
      { transform: "translate(0, 0)" },
      { transform: `translate(${to.x}rem, ${to.y}rem)` }
    ],
    {
      duration: (Math.random() + 1) * 2000, // random duration
      direction: "alternate",
      fill: "both",
      iterations: Infinity,
      easing: "ease-in-out"
    }
  );
});
