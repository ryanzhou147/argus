import { Cloudinary } from '@cloudinary/url-gen'
import { fill } from '@cloudinary/url-gen/actions/resize'
import { autoGravity } from '@cloudinary/url-gen/qualifiers/gravity'

function isCloudinaryPublicId(value: string): boolean {
  return !value.startsWith('http://') && !value.startsWith('https://')
}

/** TikTok and X media are stored as video resource type in Cloudinary. */
function isVideoPublicId(publicId: string): boolean {
  return publicId.includes('/tiktok/') || publicId.includes('/x/')
}

/** Returns true if the resolved URL should be rendered as a <video> element. */
export function isVideoUrl(imageUrl: string | null | undefined): boolean {
  if (!imageUrl) return false
  if (isCloudinaryPublicId(imageUrl)) return isVideoPublicId(imageUrl)
  return /\.(mp4|webm|mov)(\?|$)/i.test(imageUrl)
}

const CLOUD_NAME = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME as string | undefined

let cld: Cloudinary | null = null
if (CLOUD_NAME) {
  cld = new Cloudinary({ cloud: { cloudName: CLOUD_NAME } })
}

export const hasCloudinary = !!CLOUD_NAME

/**
 * Build a Cloudinary delivery URL from a public_id.
 * Uses video resource type for TikTok/X content, image for everything else.
 */
function buildCloudinaryUrl(publicId: string, width = 800, height = 450): string {
  if (!cld) return '/placeholder-event.svg'
  try {
    if (isVideoPublicId(publicId)) {
      // Video: serve as mp4, no image transforms
      const vid = cld.video(publicId)
      return vid.toURL()
    }
    const img = cld.image(publicId)
    img.resize(fill().width(width).height(height).gravity(autoGravity()))
    img.format('jpg')
    return img.toURL()
  } catch {
    return '/placeholder-event.svg'
  }
}

/**
 * Resolve media URLs using this priority:
 *
 * 1. image_url is a Cloudinary public_id (no https:// prefix)
 *    → primary = Cloudinary URL, fallback = s3_url
 *
 * 2. image_url starts with https://
 *    → primary = image_url directly (raw S3 or CDN link), fallback = null
 *
 * 3. image_url is null
 *    → primary = placeholder, fallback = null
 */
export function getMediaUrls(
  imageUrl: string | null | undefined,
  s3Url: string | null | undefined,
  width = 800,
  height = 450,
): { primary: string; fallback: string | null } {
  if (!imageUrl) {
    return { primary: '/placeholder-event.svg', fallback: null }
  }

  if (isCloudinaryPublicId(imageUrl)) {
    return {
      primary: buildCloudinaryUrl(imageUrl, width, height),
      fallback: s3Url ?? null,
    }
  }

  // Direct https:// URL (S3 or otherwise)
  return { primary: imageUrl, fallback: null }
}

/**
 * Convenience wrapper — returns just the primary URL string.
 */
export function getEventImageUrl(
  imageUrl: string | null | undefined,
  s3Url?: string | null,
  width = 800,
  height = 450,
): string {
  return getMediaUrls(imageUrl, s3Url, width, height).primary
}
