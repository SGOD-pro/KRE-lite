import React from 'react';
import { Group, Panel, Separator } from 'react-resizable-panels';
import { ChatPane } from './ChatPane';
import { SourceViewer } from './SourceViewer';

export const MainLayout: React.FC = () => {
  return (
    <div className="h-screen w-screen overflow-hidden bg-[#fcf9f6]">
      <Group orientation="horizontal" className="h-full w-full">
        {/* Left Panel: Chat Pane (~40% initial size) */}
        <Panel defaultSize={40} minSize={30} maxSize={60}>
          <ChatPane />
        </Panel>

        {/* Resizable Divider Handle */}
        <Separator className="w-1.5 bg-[#dcc1b8] hover:bg-[#9a4021] transition-colors cursor-col-resize relative flex items-center justify-center">
          <div className="w-1 h-6 rounded-full bg-[#89726b]" />
        </Separator>

        {/* Right Panel: Source Viewer (~60% initial size) */}
        <Panel defaultSize={60} minSize={40}>
          <SourceViewer />
        </Panel>
      </Group>
    </div>
  );
};
