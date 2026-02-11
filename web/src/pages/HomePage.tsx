import { Hero } from '../components/Hero';
import { Features } from '../components/Features';
import { QuickStart } from '../components/QuickStart';
import { Hotkeys } from '../components/Hotkeys';
import { Footer } from '../components/Footer';

export const HomePage = () => {
    return (
        <main>
            <Hero />
            <Features />
            <QuickStart />
            <Hotkeys />
            <Footer />
        </main>
    );
};
