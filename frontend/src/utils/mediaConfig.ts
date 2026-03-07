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
  if (!cld) return '/placeholder-event.svg'

  try {
    const img = cld.image(publicId)
    img.resize(fill().width(width).height(height).gravity(autoGravity()))
    return img.toURL()
  } catch {
    return '/placeholder-event.svg'
  }
}

export const hasCloudinary = !!CLOUD_NAME
