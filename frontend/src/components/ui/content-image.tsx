import Image from "next/image";
import { images, type ImageKey } from "@/lib/images";

/** Renders a registered image slot; empty alt marks decorative art in empty states. */
export function ContentImage({ name, className = "", priority = false, sizes }: { name: ImageKey; className?: string; priority?: boolean; sizes?: string }) {
  const image = images[name];
  return <Image src={image.src} alt={image.alt} width={image.width} height={image.height} priority={priority} sizes={sizes} className={`h-auto w-full object-cover ${className}`} />;
}
