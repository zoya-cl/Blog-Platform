import React, { useState } from 'react';
import type { QuizProps } from '../types';
import { HelpCircle, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';

export const QuizCard: React.FC<QuizProps> = ({ question, options, correct_answer, explanation }) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selectedOption === correct_answer;

  return (
    <div className="my-8 rounded-xl border border-purple-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-purple-950/30 p-6 shadow-xl">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
          <HelpCircle className="w-5 h-5" />
        </div>
        <span className="text-xs font-bold uppercase tracking-wider text-purple-400">Knowledge Check Quiz</span>
      </div>

      <h5 className="text-lg font-semibold text-slate-100 mb-5">{question}</h5>

      <div className="space-y-2.5 mb-6">
        {options.map((opt, idx) => {
          let btnStyle = "border-slate-800 bg-slate-950/60 text-slate-300 hover:border-purple-500/50 hover:bg-slate-800/50";
          
          if (submitted) {
            if (opt === correct_answer) {
              btnStyle = "border-emerald-500 bg-emerald-950/40 text-emerald-200 font-semibold ring-1 ring-emerald-500";
            } else if (opt === selectedOption) {
              btnStyle = "border-rose-500 bg-rose-950/40 text-rose-200 font-semibold ring-1 ring-rose-500";
            } else {
              btnStyle = "border-slate-800/40 bg-slate-950/30 text-slate-500 opacity-60";
            }
          } else if (selectedOption === opt) {
            btnStyle = "border-purple-500 bg-purple-950/50 text-purple-200 ring-1 ring-purple-500";
          }

          return (
            <button
              key={idx}
              disabled={submitted}
              onClick={() => setSelectedOption(opt)}
              className={`w-full text-left p-3.5 rounded-lg border transition flex items-center justify-between text-sm ${btnStyle}`}
            >
              <span>{opt}</span>
              {submitted && opt === correct_answer && (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 ml-2" />
              )}
              {submitted && opt === selectedOption && opt !== correct_answer && (
                <XCircle className="w-4 h-4 text-rose-400 shrink-0 ml-2" />
              )}
            </button>
          );
        })}
      </div>

      {!submitted ? (
        <button
          disabled={!selectedOption}
          onClick={() => setSubmitted(true)}
          className="px-5 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white font-medium text-sm flex items-center gap-2 transition shadow-lg shadow-purple-900/30"
        >
          <span>Submit Answer</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      ) : (
        <div className={`p-4 rounded-lg border text-sm ${isCorrect ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200' : 'bg-rose-950/30 border-rose-500/30 text-rose-200'}`}>
          <div className="font-semibold mb-1 flex items-center gap-2">
            {isCorrect ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-rose-400" />}
            <span>{isCorrect ? 'Correct!' : 'Incorrect'}</span>
          </div>
          <p className="text-slate-300 text-xs leading-relaxed">{explanation}</p>
        </div>
      )}
    </div>
  );
};
