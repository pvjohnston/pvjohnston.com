-- | Entry point. All rules live in "Blog.Site"; the rest of the build logic
-- (compilers, contexts, feeds, TikZ) lives in the @blog@ library.
--
-- Draft posts (@draft: true@) are excluded from the build unless the
-- @PREVIEW_DRAFTS@ environment variable is set (to anything), e.g.:
--
-- > PREVIEW_DRAFTS=1 stack exec site watch
--
-- @SKIP_TIKZ=1@ leaves @.tikzpicture@ blocks unrendered so the site can
-- build without TeX Live. PR CI uses this; the main deploy does not.
module Main (main) where

import Control.Monad (when)
import Data.Maybe (isJust)
import System.Environment (lookupEnv)
import System.IO (hPutStrLn, stderr)

import Hakyll (hakyll)

import Blog.Site (siteRules)

main :: IO ()
main = do
  previewDrafts <- isJust <$> lookupEnv "PREVIEW_DRAFTS"
  skipTikz <- isJust <$> lookupEnv "SKIP_TIKZ"
  when skipTikz $
    hPutStrLn stderr "SKIP_TIKZ is set; leaving .tikzpicture blocks unrendered"
  hakyll (siteRules previewDrafts)
