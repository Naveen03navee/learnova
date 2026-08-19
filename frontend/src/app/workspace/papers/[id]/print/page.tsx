"use client";

export const runtime = 'edge';

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";

export default function PaperPrintPage() {
  const { id } = useParams();

  const { data: paper, isLoading } = useQuery({
    queryKey: ["paper", id],
    queryFn: () => api.get(`/api/v1/papers/${id}`).then((res) => res.data),
  });

  useEffect(() => {
    if (paper) {
      // Small delay to ensure rendering is complete before print dialog
      const timer = setTimeout(() => {
        window.print();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [paper]);

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin text-blue-500 w-12 h-12" /></div>;
  }

  if (!paper) {
    return <div className="p-8 text-center">Paper not found.</div>;
  }

  // Group items by section
  const sections: Record<string, any[]> = {};
  const items = [...paper.items].sort((a, b) => a.order_index - b.order_index);
  items.forEach((item: any) => {
    if (!sections[item.section_name]) sections[item.section_name] = [];
    sections[item.section_name].push(item);
  });

  let questionNumber = 1;

  return (
    <div className="max-w-4xl mx-auto bg-white p-8 min-h-screen text-black">
      <div className="text-center mb-8 pb-4 border-b-2 border-black">
        <h1 className="text-3xl font-bold mb-2">{paper.title}</h1>
        <div className="flex justify-between text-lg mt-8">
          <span>Date: __________________</span>
          <span>Student Name: __________________</span>
        </div>
      </div>

      <div className="space-y-8">
        {Object.entries(sections).map(([sectionName, items]) => (
          <div key={sectionName} className="space-y-6">
            <h2 className="text-2xl font-bold border-b border-gray-300 pb-1">{sectionName}</h2>
            
            <div className="space-y-8">
              {items.map((item: any) => {
                const marks = item.marks_override || item.marks_snapshot;
                const options = item.content_snapshot.options;
                const currentNum = questionNumber++;
                
                return (
                  <div key={item.id} className="relative break-inside-avoid">
                    <div className="flex gap-4">
                      <span className="font-bold text-lg">{currentNum}.</span>
                      <div className="flex-1">
                        <div className="flex justify-between items-start gap-4">
                          <p className="text-lg whitespace-pre-wrap flex-1">{item.question_text_snapshot}</p>
                          <span className="text-sm font-semibold whitespace-nowrap">[{marks} Marks]</span>
                        </div>
                        
                        {options && (
                          <div className="mt-4 space-y-2">
                            {options.map((opt: any) => (
                              <div key={opt.id} className="flex gap-2 text-lg">
                                <span className="font-medium w-6">{opt.id}.</span>
                                <span>{opt.text}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {!options && (
                          <div className="mt-8 mb-16">
                            {/* Empty space for answers */}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      
      {/* Hide Print View UI styling on screen slightly, optimize for print media */}
      <style dangerouslySetInnerHTML={{__html: `
        @media print {
          body {
            background-color: white !important;
          }
          @page { margin: 1in; }
        }
      `}} />
    </div>
  );
}
