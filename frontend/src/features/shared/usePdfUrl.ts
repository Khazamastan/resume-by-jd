import { useEffect, useMemo, useState } from 'react';

import { base64ToObjectUrl } from '@/lib/pdf';

export function usePdfUrl(base64: string | null) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (base64 === null || base64 === '') {
      setObjectUrl((prev) => {
        if (prev) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
      return;
    }

    const url = base64ToObjectUrl(base64);
    setObjectUrl((prev) => {
      if (prev) {
        URL.revokeObjectURL(prev);
      }
      return url;
    });

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [base64]);

  return useMemo(() => objectUrl, [objectUrl]);
}
