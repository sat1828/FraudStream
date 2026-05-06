import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/auth', '/_next', '/favicon.ico']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  try {
    const authCookie = request.cookies.get('upi-auth')
    const token = authCookie
      ? JSON.parse(decodeURIComponent(authCookie.value)).state?.token ?? null
      : null

    if (!token) {
      const authUrl = new URL('/auth', request.url)
      authUrl.searchParams.set('callbackUrl', pathname)
      return NextResponse.redirect(authUrl)
    }
  } catch {
    const authUrl = new URL('/auth', request.url)
    authUrl.searchParams.set('callbackUrl', pathname)
    return NextResponse.redirect(authUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
