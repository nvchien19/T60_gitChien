export function BrandLogo({ size = 36, className = "", alt = "" }: { size?: number; className?: string; alt?: string }) {
  return <img src="/medicheck-logo.png" width={size} height={size} alt={alt} className={`shrink-0 rounded-md object-contain ${className}`} />;
}
