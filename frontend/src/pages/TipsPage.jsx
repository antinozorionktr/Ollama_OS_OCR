import React from 'react';
import { Lightbulb, CheckCircle, AlertCircle, Zap, ShieldAlert, FileSearch } from 'lucide-react';

const TipsPage = () => {
    const tips = [
        {
            title: "Lighting & Clarity",
            description: "Ensure the document is well-lit and the text is sharp. Avoid shadows or glares on glossy paper for optimal character detection.",
            icon: <Lightbulb className="text-amber-500" size={24} />,
            color: "bg-amber-50"
        },
        {
            title: "High Resolution",
            description: "Scan documents at 300 DPI or higher. This provides the high-fidelity detail needed for dense military reports.",
            icon: <Zap className="text-blue-500" size={24} />,
            color: "bg-blue-50"
        },
        {
            title: "Document Alignment",
            description: "Keep the document straight. While our engine auto-deskews, starting with a straight scan ensures maximum precision.",
            icon: <CheckCircle className="text-emerald-500" size={24} />,
            color: "bg-emerald-50"
        },
        {
            title: "Model Selection",
            description: "Select Llama 3.2 Vision for layout-heavy documents and Surya OCR for complex, dense text extractions.",
            icon: <FileSearch className="text-rose-500" size={24} />,
            color: "bg-rose-50"
        }
    ];

    return (
        <div className="p-8 max-w-7xl mx-auto min-h-full">
            <div className="mb-10">
                <h1 className="text-3xl font-extrabold text-[#2F353B] uppercase tracking-tight mb-2">OCR Optimization Tips</h1>
                <p className="text-[#475569] text-base font-semibold uppercase tracking-widest opacity-70">
                    Operational Guidelines for Maximum Extraction Accuracy
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {tips.map((tip, index) => (
                    <div key={index} className="group p-8 bg-white rounded-3xl border border-[#C2B280]/20 shadow-sm hover:shadow-md hover:border-[#4B5320]/30 transition-all">
                        <div className="flex items-start gap-6">
                            <div className={`p-4 ${tip.color} rounded-2xl flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform`}>
                                {tip.icon}
                            </div>
                            <div>
                                <h3 className="text-lg font-extrabold text-[#2F353B] mb-2 uppercase tracking-tight group-hover:text-[#4B5320] transition-colors">
                                    {tip.title}
                                </h3>
                                <p className="text-[#475569] leading-relaxed text-sm font-medium">
                                    {tip.description}
                                </p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
            
            <div className="mt-12 relative overflow-hidden bg-[#4B5320] rounded-[2rem] p-10 shadow-xl">
                <div className="absolute inset-0 camouflage-pattern opacity-10 pointer-events-none"></div>
                <div className="relative z-10">
                    <h2 className="text-xl font-black text-[#C2B280] mb-8 flex items-center gap-3 uppercase tracking-[0.1em]">
                        <ShieldAlert size={28} /> Pro Tips for Indian Army Documentation
                    </h2>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <li className="flex gap-4 items-start bg-white/5 p-5 rounded-2xl border border-white/10">
                            <span className="text-emerald-400 font-black text-xl leading-none">01</span>
                            <p className="text-white/90 text-sm font-bold uppercase tracking-wide leading-relaxed">
                                Ensure official stamps do not obscure critical text areas. If unavoidable, use higher contrast scanning settings.
                            </p>
                        </li>
                        <li className="flex gap-4 items-start bg-white/5 p-5 rounded-2xl border border-white/10">
                            <span className="text-emerald-400 font-black text-xl leading-none">02</span>
                            <p className="text-white/90 text-sm font-bold uppercase tracking-wide leading-relaxed">
                                For mixed layouts (text + charts), favor the Vision model to preserve the logical flow of the operational order.
                            </p>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default TipsPage;
