/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'india-saffron': '#FF9933',
                'india-white': '#FFFFFF',
                'india-green': '#138808',
                'india-navy': '#000080',
            },
            backgroundImage: {
                'tricolour-gradient': 'linear-gradient(to right, #FF9933, #FFFFFF, #138808)',
                'tricolour-vertical': 'linear-gradient(to bottom, #FF9933, #FFFFFF, #138808)',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out forwards',
                'slide-up': 'slideUp 0.5s ease-out forwards',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
            },
        },
    },
    plugins: [],
}
