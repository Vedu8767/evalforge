import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        let res: Response;
        try {
          res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/login`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                email: credentials.email,
                password: credentials.password,
              }),
            }
          );
        } catch {
          // Backend unreachable entirely (down, wrong URL, network error).
          // Throwing here (instead of returning null) lets the login page
          // show a specific message instead of "invalid credentials".
          throw new Error("backend_unreachable");
        }
        // 401 from our own /auth/login = genuinely wrong email/password.
        if (res.status === 401) return null;
        // Anything else (404 = wrong URL/stale deploy, 500 = server error,
        // etc.) is NOT a credentials problem — surface it distinctly so it
        // doesn't get shown to the user as "wrong password" when it isn't.
        if (!res.ok) {
          throw new Error(`backend_error_${res.status}`);
        }
        const data = await res.json();
        return {
          id: data.user_id,
          email: data.email,
          name: data.name,
          accessToken: data.access_token,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.accessToken = (user as any).accessToken;
        token.userId = user.id;
      }
      if (account?.provider === "google") {
        try {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/oauth/google`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                email: token.email,
                name: token.name,
                avatar_url: token.picture,
              }),
            }
          );
          if (res.ok) {
            const data = await res.json();
            token.accessToken = data.access_token;
            token.userId = data.user_id;
          }
        } catch {
          // fallback
        }
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      (session.user as any).id = token.userId;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: { strategy: "jwt" },
  secret: process.env.NEXTAUTH_SECRET,
  // Explicit cookie config. Without this, NextAuth decides the cookie name
  // (plain "next-auth.session-token" vs "__Secure-next-auth.session-token")
  // based on auto-detecting the request protocol on every request. On
  // Vercel that detection can be inconsistent across the login request and
  // the logout request, so logout can end up clearing a DIFFERENT cookie
  // name than the one login just set — leaving a stale, unclearable
  // session cookie behind that makes the next login attempt look like it
  // silently fails. Forcing this explicitly off NODE_ENV removes the
  // ambiguity entirely.
  cookies: {
    sessionToken: {
      name:
        process.env.NODE_ENV === "production"
          ? "__Secure-next-auth.session-token"
          : "next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
});

export { handler as GET, handler as POST };
