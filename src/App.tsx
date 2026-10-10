import { MotionConfig } from 'framer-motion';
import { Hero } from './components/Hero';

export default function App() {
  return (
    // "user" drops transform animations (slides, scales) when reduced motion is requested.
    <MotionConfig reducedMotion="user">
      <Hero />
    </MotionConfig>
  );
}
