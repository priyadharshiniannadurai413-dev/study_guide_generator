import React, { useState } from 'react';
import { CheckCircle2, XCircle, Download, FileText, ArrowRight, ArrowLeft, RotateCcw } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { getEffectiveToken, API_BASE } from '../../api/client';

export interface MCQItem {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

interface Props {
  questions: MCQItem[];
  topic: string;
  onRetake?: () => void;
}

export const MCQArena: React.FC<Props> = ({ questions, topic, onRetake }) => {
  let clerkAuth: any = null;
  try {
    clerkAuth = useAuth();
  } catch {
    // Graceful fallback if rendered outside Clerk AuthProvider
  }

  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<{ [index: number]: string }>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleSelectOption = (option: string) => {
    if (isSubmitted) return;
    setSelectedAnswers(prev => ({ ...prev, [currentIndex]: option }));
  };

  const calculateScore = () => {
    let score = 0;
    questions.forEach((q, idx) => {
      if (selectedAnswers[idx] === q.correct_answer) {
        score += 1;
      }
    });
    return score;
  };

  const handleDownloadCsv = () => {
    const headers = ["Question Number", "Question", "Your Answer", "Correct Answer", "Result", "Explanation"];
    const rows = questions.map((q, idx) => {
      const userAns = selectedAnswers[idx] || "Unanswered";
      const isCorrect = userAns === q.correct_answer ? "Correct" : "Incorrect";
      return [
        `Q${idx + 1}`,
        `"${q.question.replace(/"/g, '""')}"`,
        `"${userAns.replace(/"/g, '""')}"`,
        `"${q.correct_answer.replace(/"/g, '""')}"`,
        isCorrect,
        `"${q.explanation.replace(/"/g, '""')}"`
      ];
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${topic.toLowerCase().replace(/\s+/g, '_')}_mcq_results.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleDownloadPdf = async () => {
    try {
      setDownloadingPdf(true);
      let token = '';
      if (clerkAuth && clerkAuth.getToken) {
        try {
          const fresh = await clerkAuth.getToken();
          if (fresh) token = fresh;
        } catch {}
      }
      if (!token) {
        token = await getEffectiveToken();
      }

      const res = await fetch(`${API_BASE}/api/study/export-pack/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          title: topic,
          difficulty: "intermediate",
          concise_summary: "MCQ Practice Assessment Summary",
          suggested_study_order: [],
          glossary: [],
          mcqs: questions,
          short_answers: []
        })
      });

      if (!res.ok) throw new Error("Failed to export PDF");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${topic.toLowerCase().replace(/\s+/g, '_')}_quiz_sheet.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Error generating PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const currentQ = questions[currentIndex] || {
    question: '',
    options: [],
    correct_answer: '',
    explanation: '',
  };

  if (isSubmitted) {
    const finalScore = calculateScore();
    const percentage = questions.length > 0 ? Math.round((finalScore / questions.length) * 100) : 0;

    return (
      <div className="max-w-4xl mx-auto my-8 p-6 bg-slate-900 border border-slate-800 rounded-2xl text-slate-100 space-y-8">
        {/* Score Summary Banner */}
        <div className="flex flex-col md:flex-row items-center justify-between p-6 bg-slate-950 border border-slate-800 rounded-xl gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Exam Results: {topic}</h2>
            <p className="text-sm text-slate-400 mt-1">
              Score: <strong className="text-indigo-400 text-lg">{finalScore} / {questions.length}</strong> ({percentage}%)
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleDownloadCsv}
              className="flex items-center px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg transition border border-slate-700"
            >
              <Download className="w-4 h-4 mr-1.5 text-cyan-400"/>
              Download CSV (Anki)
            </button>
            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition"
            >
              <FileText className="w-4 h-4 mr-1.5"/>
              {downloadingPdf ? "Generating..." : "Download PDF"}
            </button>
            <button
              onClick={() => {
                setSelectedAnswers({});
                setIsSubmitted(false);
                setCurrentIndex(0);
                if (onRetake) onRetake();
              }}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition"
              title="Retake Quiz"
            >
              <RotateCcw className="w-4 h-4"/>
            </button>
          </div>
        </div>

        {/* Complete Answer Key Section */}
        <div className="space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3">Complete Answer Key & Rationales</h3>
          {questions.map((q, idx) => {
            const userChoice = selectedAnswers[idx];
            const isCorrect = userChoice === q.correct_answer;

            return (
              <div key={idx} className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
                <div className="flex items-start justify-between">
                  <span className="text-sm font-semibold text-white">
                    {idx + 1}. {q.question}
                  </span>
                  {isCorrect ? (
                    <span className="flex items-center text-xs font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="w-3 h-3 mr-1"/> Correct
                    </span>
                  ) : (
                    <span className="flex items-center text-xs font-medium text-rose-400 bg-rose-950/60 border border-rose-800 px-2 py-0.5 rounded-full">
                      <XCircle className="w-3 h-3 mr-1"/> Incorrect
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  {q.options.map((opt, oIdx) => {
                    const isSelected = userChoice === opt;
                    const isAnswer = opt === q.correct_answer;

                    let badgeClass = "bg-slate-900 border-slate-800 text-slate-400";
                    if (isAnswer) {
                      badgeClass = "bg-emerald-950/40 border-emerald-600 text-emerald-300 font-semibold";
                    } else if (isSelected && !isAnswer) {
                      badgeClass = "bg-rose-950/40 border-rose-600 text-rose-300 line-through";
                    }

                    return (
                      <div key={oIdx} className={`p-2.5 rounded-lg border ${badgeClass}`}>
                        {String.fromCharCode(65 + oIdx)}. {opt}
                      </div>
                    );
                  })}
                </div>

                <div className="p-3 bg-slate-900/80 rounded-lg text-xs text-slate-300 border border-slate-800 leading-relaxed">
                  <strong className="text-indigo-400">Explanation: </strong> {q.explanation}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto my-8 p-6 bg-slate-900 border border-slate-800 rounded-2xl text-slate-100 shadow-xl space-y-6">
      {/* Test Progress Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">Exam Mode</span>
          <h2 className="text-lg font-bold text-white">{topic}</h2>
        </div>
        <div className="text-xs font-medium text-slate-400 bg-slate-800 px-3 py-1 rounded-full border border-slate-700">
          Question {currentIndex + 1} of {questions.length}
        </div>
      </div>

      {/* Active Question Box */}
      <div className="space-y-4">
        <h3 className="text-base font-semibold text-slate-200 leading-relaxed">
          {currentIndex + 1}. {currentQ.question}
        </h3>

        <div className="space-y-2.5">
          {currentQ.options.map((option, idx) => {
            const isSelected = selectedAnswers[currentIndex] === option;
            return (
              <button
                key={idx}
                onClick={() => handleSelectOption(option)}
                className={`w-full text-left p-3.5 rounded-xl border text-sm transition ${
                  isSelected
                    ? "bg-indigo-600/20 border-indigo-500 text-white font-medium"
                    : "bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900"
                }`}
              >
                <span className="font-semibold text-indigo-400 mr-2">{String.fromCharCode(65 + idx)}.</span>
                {option}
              </button>
            );
          })}
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between border-t border-slate-800 pt-4">
        <button
          onClick={() => setCurrentIndex(prev => Math.max(prev - 1, 0))}
          disabled={currentIndex === 0}
          className="flex items-center px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg disabled:opacity-30 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5"/> Previous
        </button>

        {currentIndex < questions.length - 1 ? (
          <button
            onClick={() => setCurrentIndex(prev => Math.min(prev + 1, questions.length - 1))}
            className="flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition"
          >
            Next <ArrowRight className="w-4 h-4 ml-1.5"/>
          </button>
        ) : (
          <button
            onClick={() => setIsSubmitted(true)}
            className="flex items-center px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg shadow transition"
          >
            Submit Exam
          </button>
        )}
      </div>
    </div>
  );
};
