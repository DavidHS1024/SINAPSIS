export default function StepProgress({ steps, completedSteps }) {
  return (
    <div className="flex items-center w-full my-4">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.includes(step.id);
        const isActive = !isCompleted && (index === 0 || completedSteps.includes(steps[index-1].id));
        
        let circleClass = "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 transition-colors ";
        let lineClass = "flex-1 h-1 transition-colors ";
        
        if (isCompleted) {
          circleClass += "bg-acento border-acento text-marino-900";
          lineClass += "bg-acento";
        } else if (isActive) {
          circleClass += "bg-marino-800 border-acento text-acento animate-pulse";
          lineClass += "bg-marino-700";
        } else {
          circleClass += "bg-marino-900 border-marino-700 text-marino-600";
          lineClass += "bg-marino-700";
        }

        return (
          <div key={step.id} className="flex items-center flex-1 last:flex-none">
            <div className="relative flex flex-col items-center">
              <div className={circleClass}>
                {isCompleted ? "✓" : index + 1}
              </div>
              <div className="absolute top-10 w-24 text-center text-[10px] tracking-wide text-niebla/70">
                {step.label}
              </div>
            </div>
            {index < steps.length - 1 && (
              <div className={lineClass} />
            )}
          </div>
        );
      })}
    </div>
  );
}
