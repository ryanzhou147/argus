import { Cloudinary } from '@cloudinary/url-gen'
import { fill } from '@cloudinary/url-gen/actions/resize'
import { autoGravity } from '@cloudinary/url-gen/qualifiers/gravity'

const CLOUD_NAME = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME as string | undefined

let cld: Cloudinary | null = null
if (CLOUD_NAME) {
  cld = new Cloudinary({ cloud: { cloudName: CLOUD_NAME } })
}

/**
 * Build a Cloudinary URL for the given public ID when credentials are set.
 * Falls back to a local placeholder when VITE_CLOUDINARY_CLOUD_NAME is absent.
 */
export function getEventImageUrl(publicId: string | null | undefined, width = 800, height = 450): string {
  if (!publicId) return '/placeholder-event.svg'

  // If it's already a full URL (S3 or other), return it directly
  if (publicId.startsWith('http://') || publicId.startsWith('https://')) {
    return publicId
  }

  if (!cld) return '/placeholder-event.svg'

  try {
    const img = cld.image(publicId)
    img.resize(fill().width(width).height(height).gravity(autoGravity()))
    img.format('jpg') // forces JPEG delivery; also generates a thumbnail if publicId is a video asset
    return img.toURL()
  } catch {
    return '/placeholder-event.svg'
  }
}

export const hasCloudinary = !!CLOUD_NAME

/**
 * Returns { primary: Cloudinary URL, fallback: S3 URL | null }
 * Primary is the Cloudinary-transformed URL (720x720 square fill).
 * Fallback is the raw S3 URL, used in <img onError>.
 */
const VIDEO_EXTENSIONS = /\.(mp4|mov|webm|avi|mkv|m4v)$/i

export function isVideoUrl(url: string | null | undefined): boolean {
  if (!url) return false
  return VIDEO_EXTENSIONS.test(url)
}

const VIDEO_PUBLIC_ID_PREFIXES = ['hackcanada/x/', 'hackcanada/tiktok/']

function isVideoPublicId(publicId: string | null | undefined): boolean {
  if (!publicId) return false
  return isVideoUrl(publicId) || VIDEO_PUBLIC_ID_PREFIXES.some(p => publicId.startsWith(p))
}

/**
 * Build a Cloudinary *video* delivery URL.
 * Uses /video/upload/ (not /image/upload/) so Cloudinary serves the actual mp4.
 */
function getCloudinaryVideoUrl(publicId: string): string | null {
  if (!cld) return null
  try {
    const vid = cld.video(publicId)
    return vid.toURL()
  } catch {
    return null
  }
}

/**
 * Build a Cloudinary thumbnail (JPEG) from a video asset.
 * Uses /video/upload/ with .format('jpg') so Cloudinary extracts a frame.
 */
function getCloudinaryVideoThumb(publicId: string, width = 800, height = 450): string | null {
  if (!cld) return null
  try {
    const vid = cld.video(publicId)
    vid.resize(fill().width(width).height(height).gravity(autoGravity()))
    vid.format('jpg')
    return vid.toURL()
  } catch {
    return null
  }
}

/**
 * Returns { primary, isVideo, fallback }
 * - primary: best available media URL (Cloudinary > direct URL > placeholder)
 * - isVideo: true when the resolved URL is a video file
 * - fallback: secondary URL to try on error (images only)
 */
export function getMediaUrls(
  publicId: string | null | undefined,
  s3Url: string | null | undefined
): { primary: string; isVideo: boolean; fallback: string | null } {
  const pubIsVideo = isVideoPublicId(publicId)

  if (pubIsVideo && publicId) {
    const videoUrl = getCloudinaryVideoUrl(publicId)
    if (videoUrl) {
      const thumbUrl = getCloudinaryVideoThumb(publicId)
      return { primary: videoUrl, isVideo: true, fallback: thumbUrl }
    }
  }

  const cloudUrl = getEventImageUrl(publicId)
  const cloudFailed = cloudUrl === '/placeholder-event.svg'

  if (!cloudFailed && !pubIsVideo) {
    const s3IsImage = s3Url && !isVideoUrl(s3Url)
    return { primary: cloudUrl, isVideo: false, fallback: s3IsImage ? s3Url : null }
  }

  if (s3Url) {
    const s3IsVideo = isVideoUrl(s3Url)
    return { primary: s3Url, isVideo: s3IsVideo, fallback: null }
  }

  return { primary: '/placeholder-event.svg', isVideo: false, fallback: null }
}
