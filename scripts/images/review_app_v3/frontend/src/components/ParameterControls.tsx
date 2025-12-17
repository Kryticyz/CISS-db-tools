import { useCallback, useEffect, useState } from 'react';
import type { AnalysisParameters, ParameterInfo } from '../types';

interface ParameterControlsProps {
  params: AnalysisParameters;
  paramInfo: ParameterInfo[];
  onChange: (key: keyof AnalysisParameters, value: number) => void;
  activeTab: 'duplicates' | 'similar' | 'outliers';
}

function ParameterControls({
  params,
  paramInfo,
  onChange,
  activeTab,
}: ParameterControlsProps) {
  // Filter parameters based on active tab
  const relevantParams = paramInfo.filter((p) => {
    if (activeTab === 'duplicates') {
      return p.name === 'hash_size' || p.name === 'hamming_threshold';
    }
    if (activeTab === 'similar') {
      return p.name === 'similarity_threshold';
    }
    if (activeTab === 'outliers') {
      return p.name === 'threshold_percentile';
    }
    return false;
  });

  if (relevantParams.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {relevantParams.map((param) => (
        <ParameterSlider
          key={param.name}
          param={param}
          value={params[param.name as keyof AnalysisParameters]}
          onChange={(value) => onChange(param.name as keyof AnalysisParameters, value)}
        />
      ))}
    </div>
  );
}

interface ParameterSliderProps {
  param: ParameterInfo;
  value: number;
  onChange: (value: number) => void;
}

function ParameterSlider({ param, value, onChange }: ParameterSliderProps) {
  // Local state for immediate UI feedback
  const [localValue, setLocalValue] = useState(value);

  // Sync with external value
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounced onChange
  const handleChange = useCallback(
    (newValue: number) => {
      setLocalValue(newValue);
      // Debounce the actual onChange call
      const timeoutId = setTimeout(() => {
        onChange(newValue);
      }, 300);
      return () => clearTimeout(timeoutId);
    },
    [onChange]
  );

  return (
    <div className="space-y-2">
      {/* Label with value */}
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">
          {param.label}
        </label>
        <span className="text-sm font-mono text-gray-500">
          {param.type === 'float' ? localValue.toFixed(2) : localValue}
        </span>
      </div>

      {/* Slider */}
      <input
        type="range"
        min={param.min}
        max={param.max}
        step={param.step}
        value={localValue}
        onChange={(e) => handleChange(parseFloat(e.target.value))}
        className="slider"
      />

      {/* Description */}
      <p className="text-xs text-gray-500">{param.description}</p>
    </div>
  );
}

export default ParameterControls;
